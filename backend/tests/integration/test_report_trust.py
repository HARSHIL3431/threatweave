"""P0-3 tests: PDF/report export trustworthiness.

Production exports must use genuine pipeline data; mismatched, missing, or
failed analyses must surface as controlled errors, never as plausible
success reports. PDF *content* (via pypdf) is asserted, not just status.
Hermetic: frozen ML artifacts, fake-index RAG, temp report dirs, no LLM calls.
"""
import copy
import io
import re

from pypdf import PdfReader

from app.dependencies import (
    get_ml_service,
    get_rag_service_evidence,
    get_report_service,
)
from app.main import app
from app.services.rag_service import RagService
from app.services.report_service import ReportService


def _docs():
    return [
        {
            "text": "Technique: Network Service Discovery (T-TEST-1)\nDescription: Scan open ports",
            "meta": {
                "technique_id": "T-TEST-1", "technique_name": "Network Service Discovery",
                "type": "technique", "tactics": ["discovery"],
                "description": "Scan open ports for identifying services.",
                "detection": "Watch for repeated connections",
                "mitigations": ["M-FIRST"],
                "data_sources": [], "platforms": [],
            },
        },
    ]


def _override(make_store, tmp_path, fake_embedder, *, rag=True, report_dir=None):
    if rag:
        index_path, metadata_path = make_store(_docs())
        app.dependency_overrides[get_rag_service_evidence] = lambda: RagService(
            enabled=True, index_path=index_path, metadata_path=metadata_path,
            embedder=fake_embedder, top_k=5,
        )
    else:
        app.dependency_overrides[get_rag_service_evidence] = lambda: RagService(
            enabled=False, embedder=None
        )
    app.dependency_overrides[get_report_service] = lambda: ReportService(
        output_dir=report_dir or tmp_path / "reports"
    )


def _payload(sample_flows, **overrides):
    payload = {
        "report_type": "analysis",
        "request_id": "report-trust-req-1",
        "app_name": "AI-Powered Cybersecurity Anomaly Detection System",
        "flow": copy.deepcopy(sample_flows["anomalous_flow"]["input"]),
        "top_k": 5,
    }
    payload.update(overrides)
    return payload


def _pdf_text(report_dir, file_name):
    return "".join(
        page.extract_text() or ""
        for page in PdfReader(io.BytesIO((report_dir / file_name).read_bytes())).pages
    )


def _no_pdfs(report_dir):
    return list(report_dir.glob("report_*.pdf")) == []


# A. report_type must not contradict the computed outcome.
def test_report_type_anomaly_rejected_for_benign_flow(
    client, loaded_ml_service, sample_flows, make_store, tmp_path, fake_embedder
):
    app.dependency_overrides[get_ml_service] = lambda: loaded_ml_service
    report_dir = tmp_path / "reports"
    _override(make_store, tmp_path, fake_embedder, rag=True, report_dir=report_dir)
    try:
        payload = _payload(
            sample_flows,
            report_type="anomaly",
            flow=copy.deepcopy(sample_flows["benign_flow"]["input"]),
        )
        resp = client.post("/api/v1/reports/generate", json=payload)
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "INVALID_INPUT"
    assert _no_pdfs(report_dir)


def test_report_type_benign_rejected_for_anomalous_flow(
    client, loaded_ml_service, sample_flows, make_store, tmp_path, fake_embedder
):
    app.dependency_overrides[get_ml_service] = lambda: loaded_ml_service
    report_dir = tmp_path / "reports"
    _override(make_store, tmp_path, fake_embedder, rag=True, report_dir=report_dir)
    try:
        resp = client.post(
            "/api/v1/reports/generate",
            json=_payload(sample_flows, report_type="benign"),
        )
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "INVALID_INPUT"
    assert _no_pdfs(report_dir)


def test_report_type_analysis_accepted_for_both_outcomes(
    client, loaded_ml_service, sample_flows, make_store, tmp_path, fake_embedder
):
    app.dependency_overrides[get_ml_service] = lambda: loaded_ml_service
    report_dir = tmp_path / "reports"
    _override(make_store, tmp_path, fake_embedder, rag=True, report_dir=report_dir)
    try:
        anomalous = client.post("/api/v1/reports/generate", json=_payload(sample_flows))
        benign_payload = _payload(
            sample_flows,
            flow=copy.deepcopy(sample_flows["benign_flow"]["input"]),
        )
        benign = client.post("/api/v1/reports/generate", json=benign_payload)
    finally:
        app.dependency_overrides.clear()
    assert anomalous.status_code == 200
    assert benign.status_code == 200
    assert _pdf_text(report_dir, anomalous.json()["file_name"]).count("ANOMALOUS") >= 1
    assert "BENIGN" in _pdf_text(report_dir, benign.json()["file_name"])


# B. PDF carries the genuine identifiers and pipeline values.
def test_pdf_contains_genuine_identifiers_and_values(
    client, loaded_ml_service, sample_flows, make_store, tmp_path, fake_embedder
):
    app.dependency_overrides[get_ml_service] = lambda: loaded_ml_service
    report_dir = tmp_path / "reports"
    _override(make_store, tmp_path, fake_embedder, rag=True, report_dir=report_dir)
    try:
        resp = client.post("/api/v1/reports/generate", json=_payload(sample_flows))
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200
    data = resp.json()
    text = _pdf_text(report_dir, data["file_name"])
    assert data["report_id"] in text
    assert "report-trust-req-1" in text
    assert "0.540229" in text  # genuine fixture score, not caller-supplied
    assert "with_port" in text
    assert "T-TEST-1" in text


# C. Callers cannot substitute detection fields into a production export.
def test_caller_supplied_detection_fields_rejected(
    client, loaded_ml_service, sample_flows, make_store, tmp_path, fake_embedder
):
    app.dependency_overrides[get_ml_service] = lambda: loaded_ml_service
    report_dir = tmp_path / "reports"
    _override(make_store, tmp_path, fake_embedder, rag=True, report_dir=report_dir)
    try:
        payload = _payload(sample_flows)
        payload["anomaly_score"] = 0.99  # not a schema field: must be refused
        resp = client.post("/api/v1/reports/generate", json=payload)
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 422
    assert _no_pdfs(report_dir)


# D. Failed validation writes no report file.
def test_fabricated_llm_writes_no_file(
    client, loaded_ml_service, sample_flows, make_store, tmp_path, fake_embedder
):
    app.dependency_overrides[get_ml_service] = lambda: loaded_ml_service
    report_dir = tmp_path / "reports"
    _override(make_store, tmp_path, fake_embedder, rag=True, report_dir=report_dir)
    try:
        payload = _payload(sample_flows)
        payload["llm_explanation"] = {
            "summary": "S", "anomaly_assessment": "A", "observed_indicators": [],
            "potential_attack_context": [
                {"technique_id": "T9999", "technique_name": "Fake",
                 "confidence": "high", "reason": "hallucinated"}
            ],
            "recommended_actions": [], "limitations": [],
        }
        resp = client.post("/api/v1/reports/generate", json=payload)
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 502
    assert resp.json()["error_code"] == "LLM_VALIDATION_ERROR"
    assert _no_pdfs(report_dir)


# E. Empty evidence is honest; detection still stands on its own.
def test_empty_evidence_represented_honestly(
    client, loaded_ml_service, sample_flows, make_store, tmp_path, fake_embedder
):
    app.dependency_overrides[get_ml_service] = lambda: loaded_ml_service
    report_dir = tmp_path / "reports"
    _override(make_store, tmp_path, fake_embedder, rag=False, report_dir=report_dir)
    try:
        resp = client.post("/api/v1/reports/generate", json=_payload(sample_flows))
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200
    text = _pdf_text(report_dir, resp.json()["file_name"])
    assert "ANOMALOUS" in text  # genuine detection unaffected by missing RAG/LLM
    assert "No MITRE ATT&CK context was retrieved" in text
    assert "No LLM explanation was available" in text
    assert "T-TEST-1" not in text  # absence is not filled in


# F. Missing optional data is generated, never fabricated.
def test_auto_request_id_echoed_in_pdf(
    client, loaded_ml_service, sample_flows, make_store, tmp_path, fake_embedder
):
    app.dependency_overrides[get_ml_service] = lambda: loaded_ml_service
    report_dir = tmp_path / "reports"
    _override(make_store, tmp_path, fake_embedder, rag=True, report_dir=report_dir)
    try:
        payload = _payload(sample_flows)
        del payload["request_id"]
        resp = client.post("/api/v1/reports/generate", json=payload)
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200
    request_id = resp.json()["request_id"]
    assert re.fullmatch(r"[0-9a-f-]{36}", request_id)
    assert request_id in _pdf_text(report_dir, resp.json()["file_name"])


# G. Nonexistent analyses surface as controlled errors.
def test_unknown_and_malformed_download_ids_are_404(
    client, make_store, tmp_path, fake_embedder
):
    _override(make_store, tmp_path, fake_embedder, rag=False, report_dir=tmp_path / "r")
    try:
        # Traversal attempts never resolve into the report store (router-level 404).
        for bad in ("../../../../etc/passwd", "..%2F..%2Fetc%2Fpasswd"):
            assert client.get(f"/api/v1/reports/{bad}/download").status_code == 404
        # Well-formed-but-unknown ids reach the handler: controlled REPORT_NOT_FOUND.
        for bad_id in ("f" * 32, "abc"):
            resp = client.get(f"/api/v1/reports/{bad_id}/download")
            assert resp.status_code == 404
            assert resp.json()["error_code"] == "REPORT_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()
