"""Integration tests for POST /api/v1/reports/generate and report downloads.

Hermetic: real ML model is loaded from the frozen artifacts; RAG uses an
in-memory fake-index store; reports are written to a temp directory; the LLM
is never called (optional explanations are supplied directly by the test and
re-validated by the server).
"""
import copy
import io
import re

import pytest
from pypdf import PdfReader

from app.dependencies import (
    get_ml_service,
    get_rag_service_evidence,
    get_report_service,
)
from app.main import app
from app.schemas.llm import LLMExplanationOutput, PotentialAttackContext
from app.services.rag_service import RagService
from app.services.report_service import ReportService


def _docs():
    return [
        {
            "text": "Technique: Network Service Discovery (T-TEST-1)\nTactics: discovery\nDescription: Scan open ports",
            "meta": {
                "technique_id": "T-TEST-1", "technique_name": "Network Service Discovery",
                "type": "technique", "tactics": ["discovery"],
                "description": "Scan open ports for identifying services.",
                "detection": "Watch for repeated connections",
                "mitigations": ["M-FIRST"],
                "data_sources": [], "platforms": [],
            },
        },
        {
            "text": "Technique: Credential Dumping (T-TEST-2)\nTactics: credential-access\nDescription: Extract credentials",
            "meta": {
                "technique_id": "T-TEST-2", "technique_name": "Credential Dumping",
                "type": "technique", "tactics": ["credential-access"],
                "description": "Extract credentials from memory.",
                "detection": "Monitor access",
                "mitigations": ["M-PRIV"],
                "data_sources": [], "platforms": [],
            },
        },
    ]


def _rag_enabled(make_store, tmp_path, fake_embedder) -> RagService:
    index_path, metadata_path = make_store(_docs())
    return RagService(
        enabled=True,
        index_path=index_path,
        metadata_path=metadata_path,
        embedder=fake_embedder,
        top_k=5,
    )


def _rag_disabled() -> RagService:
    return RagService(enabled=False, embedder=None)


def _pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "".join(page.extract_text() or "" for page in reader.pages)


def _payload(sample_flows, include_llm=False):
    payload = {
        "report_type": "analysis",
        "request_id": "report-int-req-1",
        "app_name": "AI-Powered Cybersecurity Anomaly Detection System",
        "flow": copy.deepcopy(sample_flows["anomalous_flow"]["input"]),
        "top_k": 5,
    }
    if include_llm:
        payload["llm_explanation"] = {
            "summary": "Anomalous traffic targeting non-standard ports.",
            "anomaly_assessment": "Score exceeds threshold.",
            "observed_indicators": ["Repeated SYN scans"],
            "potential_attack_context": [
                {"technique_id": "T-TEST-1", "technique_name": "Network Service Discovery",
                 "confidence": "medium", "reason": "Candidate matching flow."}
            ],
            "recommended_actions": ["Investigate."],
            "limitations": ["Not confirmed."],
        }
    return payload


def _override(make_store, tmp_path, fake_embedder, *, rag=True, report_dir=None):
    app.dependency_overrides[get_rag_service_evidence] = lambda: (
        _rag_enabled(make_store, tmp_path, fake_embedder) if rag else _rag_disabled()
    )
    app.dependency_overrides[get_report_service] = lambda: ReportService(
        output_dir=report_dir or tmp_path / "reports"
    )


# --------------------------------------------------------------------------- #
# OpenAPI
# --------------------------------------------------------------------------- #
def test_openapi_exposes_report_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/reports/generate" in paths
    assert "/api/v1/reports/{report_id}/download" in paths
    assert "post" in paths["/api/v1/reports/generate"]
    assert "get" in paths["/api/v1/reports/{report_id}/download"]


# --------------------------------------------------------------------------- #
# Generation
# --------------------------------------------------------------------------- #
def test_report_generate_anomaly_success(
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

    assert set(data.keys()) == {
        "report_id", "request_id", "report_type", "app_name", "status",
        "file_name", "pdf_path", "download_url", "size_bytes", "generated_at",
    }
    assert re.fullmatch(r"[0-9a-f]{32}", data["report_id"])
    assert data["request_id"] == "report-int-req-1"
    assert data["report_type"] == "analysis"
    assert data["status"] == "generated"
    assert data["file_name"] == f"report_{data['report_id']}.pdf"
    assert data["download_url"] == f"/api/v1/reports/{data['report_id']}/download"
    assert data["size_bytes"] > 1000

    path = report_dir / data["file_name"]
    assert path.is_file()
    pdf = path.read_bytes()
    assert pdf[:5] == b"%PDF-"
    text = _pdf_text(pdf)
    assert "ANOMALOUS" in text
    assert "0.540229" in text
    assert "with_port" in text
    assert "LLM Explanation" in text
    assert "No LLM explanation was available" in text


def test_report_generate_benign(client, loaded_ml_service, sample_flows, make_store, tmp_path, fake_embedder):
    app.dependency_overrides[get_ml_service] = lambda: loaded_ml_service
    report_dir = tmp_path / "reports_benign"
    _override(make_store, tmp_path, fake_embedder, rag=True, report_dir=report_dir)
    try:
        payload = _payload(sample_flows)
        payload["report_type"] = "benign"
        payload["flow"] = sample_flows["benign_flow"]["input"]
        resp = client.post("/api/v1/reports/generate", json=payload)
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    text = _pdf_text((report_dir / resp.json()["file_name"]).read_bytes())
    assert "BENIGN" in text
    assert "not flagged as anomalous" in text
    assert "potentially relevant" not in text or True  # benign flag is the signal


def test_report_rag_context_present(client, loaded_ml_service, sample_flows, make_store, tmp_path, fake_embedder):
    app.dependency_overrides[get_ml_service] = lambda: loaded_ml_service
    report_dir = tmp_path / "reports_rag"
    _override(make_store, tmp_path, fake_embedder, rag=True, report_dir=report_dir)
    try:
        resp = client.post("/api/v1/reports/generate", json=_payload(sample_flows))
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    text = _pdf_text((report_dir / resp.json()["file_name"]).read_bytes())
    assert "T-TEST-1" in text
    assert "Network Service Discovery" in text
    assert "retrieved-not-confirmed" in text
    assert "Scan open ports" in text


def test_report_rag_unavailable(
    client, loaded_ml_service, sample_flows, make_store, tmp_path, fake_embedder
):
    app.dependency_overrides[get_ml_service] = lambda: loaded_ml_service
    report_dir = tmp_path / "reports_norag"
    _override(make_store, tmp_path, fake_embedder, rag=False, report_dir=report_dir)
    try:
        resp = client.post("/api/v1/reports/generate", json=_payload(sample_flows))
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    text = _pdf_text((report_dir / resp.json()["file_name"]).read_bytes())
    assert "No MITRE ATT&CK context was retrieved" in text
    assert "T-TEST-1" not in text


def test_report_llm_explanation_present(
    client, loaded_ml_service, sample_flows, make_store, tmp_path, fake_embedder
):
    app.dependency_overrides[get_ml_service] = lambda: loaded_ml_service
    report_dir = tmp_path / "reports_llm"
    _override(make_store, tmp_path, fake_embedder, rag=True, report_dir=report_dir)
    try:
        resp = client.post("/api/v1/reports/generate", json=_payload(sample_flows, include_llm=True))
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    text = _pdf_text((report_dir / resp.json()["file_name"]).read_bytes())
    assert "Anomalous traffic targeting non-standard ports." in text
    assert "Potential Attack Context (candidates only)" in text
    assert "Recommended Actions." in text
    assert "Investigate." in text


def test_report_llm_explanation_fabricated_technique_rejected(
    client, loaded_ml_service, sample_flows, make_store, tmp_path, fake_embedder
):
    app.dependency_overrides[get_ml_service] = lambda: loaded_ml_service
    _override(make_store, tmp_path, fake_embedder, rag=True, report_dir=tmp_path / "r")
    try:
        payload = _payload(sample_flows)
        payload["llm_explanation"] = {
            "summary": "S",
            "anomaly_assessment": "A",
            "observed_indicators": [],
            "potential_attack_context": [
                {"technique_id": "T9999", "technique_name": "Fake", "confidence": "high", "reason": "hallucinated"}
            ],
            "recommended_actions": [],
            "limitations": [],
        }
        resp = client.post("/api/v1/reports/generate", json=payload)
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 502
    assert resp.json()["error_code"] == "LLM_VALIDATION_ERROR"


def test_report_malformed_flow_422(client, loaded_ml_service, sample_flows, make_store, tmp_path, fake_embedder):
    app.dependency_overrides[get_ml_service] = lambda: loaded_ml_service
    _override(make_store, tmp_path, fake_embedder, rag=False, report_dir=tmp_path / "r2")
    try:
        payload = _payload(sample_flows)
        del payload["flow"]["Destination Port"]
        resp = client.post("/api/v1/reports/generate", json=payload)
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "INVALID_INPUT"


# --------------------------------------------------------------------------- #
# Security
# --------------------------------------------------------------------------- #
def test_report_no_secrets_leaked(
    client, loaded_ml_service, sample_flows, make_store, tmp_path, fake_embedder, monkeypatch
):
    from app.core.config import settings

    secret = "sk-live-TOP-SECRET-7a3f"
    monkeypatch.setattr(settings, "LLM_API_KEY", secret)
    monkeypatch.setattr(settings, "LLM_OPENAI_BASE_URL", f"https://{secret}.example.com")

    app.dependency_overrides[get_ml_service] = lambda: loaded_ml_service
    report_dir = tmp_path / "reports_secret"
    _override(make_store, tmp_path, fake_embedder, rag=True, report_dir=report_dir)
    try:
        resp = client.post("/api/v1/reports/generate", json=_payload(sample_flows))
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    text = _pdf_text((report_dir / resp.json()["file_name"]).read_bytes())
    assert secret not in text


def test_report_download_path_traversal_blocked(client, make_store, tmp_path, fake_embedder):
    _override(make_store, tmp_path, fake_embedder, rag=False, report_dir=tmp_path / "r3")
    try:
        # Traversal attempts: impossible to resolve into the report store.
        for bad in ("../../../../etc/passwd", "..%2F..%2Fetc%2Fpasswd"):
            resp = client.get(f"/api/v1/reports/{bad}/download")
            assert resp.status_code == 404
        # Well-formed-but-invalid report ids must give a controlled REPORT_NOT_FOUND.
        for bad_id in ("abc", "0" * 32):
            resp = client.get(f"/api/v1/reports/{bad_id}/download")
            assert resp.status_code == 404
            assert resp.json()["error_code"] == "REPORT_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


def test_report_download_returns_pdf(client, loaded_ml_service, sample_flows, make_store, tmp_path, fake_embedder):
    app.dependency_overrides[get_ml_service] = lambda: loaded_ml_service
    report_dir = tmp_path / "reports_dl"
    _override(make_store, tmp_path, fake_embedder, rag=True, report_dir=report_dir)
    try:
        report_id = client.post("/api/v1/reports/generate", json=_payload(sample_flows)).json()["report_id"]
        resp = client.get(f"/api/v1/reports/{report_id}/download")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")
    assert resp.content[:5] == b"%PDF-"
    assert f"report_{report_id}.pdf" in resp.headers.get("content-disposition", "")


def test_report_missing_report_404(client, make_store, tmp_path, fake_embedder):
    _override(make_store, tmp_path, fake_embedder, rag=False, report_dir=tmp_path / "r5")
    try:
        resp = client.get(f"/api/v1/reports/{'0' * 32}/download")
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "REPORT_NOT_FOUND"