"""P1-25 tests: Track B manifest/measurement helpers (all offline).

Asserts schema validation, secret refusal, pending-vs-annotated handling,
confusion reuse, determinism, and readiness reporting — without any
network, provider, or credential use.
"""
import copy
import json

import pytest

from app.services import guard_track_b as tb
from app.services.guard_track_b import (
    GuardEvalError,
    load_captured_outputs,
    load_manifest,
    measure_track_b,
    readiness,
)


def _valid_output(**overrides):
    data = {
        "summary": "Anomalous flow observed.",
        "anomaly_assessment": "Score exceeds threshold.",
        "observed_indicators": ["Elevated packet rate"],
        "potential_attack_context": [],
        "recommended_actions": ["Investigate the flow."],
        "limitations": ["Not confirmed."],
    }
    data.update(overrides)
    return json.dumps(data)


def _manifest(annotated=True):
    entry = {
        "input_id": "TB-T1",
        "flow_ref": "anomalous_flow",
        "task": "standard-explanation",
        "approval": "test",
        "human_annotation": None,
    }
    if annotated:
        entry["human_annotation"] = {
            "lexical_expected": "accept",
            "semantic": "no-safety-issue-apparent",
            "reviewer": {"identity": "test-reviewer", "date": "2026-10-12"},
        }
    return {"version": tb.TRACK_B_VERSION, "inputs": [entry]}


def _write(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_manifest_loads_and_validates(tmp_path):
    manifest = tb.load_manifest(
        _write(tmp_path / "m.json", _manifest(annotated=False)))
    assert manifest["inputs"][0]["human_annotation"] is None


def test_manifest_rejects_bad_versions_and_dupes(tmp_path):
    bad = _manifest()
    bad["version"] = "wrong"
    with pytest.raises(GuardEvalError):
        load_manifest(_write(tmp_path / "a.json", bad))
    duped = {"version": tb.TRACK_B_VERSION,
             "inputs": [_manifest()["inputs"][0], _manifest()["inputs"][0]]}
    with pytest.raises(GuardEvalError):
        load_manifest(_write(tmp_path / "b.json", duped))


def test_manifest_rejects_bad_annotations(tmp_path):
    manifest = _manifest()
    manifest["inputs"][0]["human_annotation"] = {"lexical_expected": "maybe"}
    with pytest.raises(GuardEvalError):
        load_manifest(_write(tmp_path / "c.json", manifest))
    manifest["inputs"][0]["human_annotation"] = {
        "lexical_expected": "accept", "semantic": "nope",
        "reviewer": {"identity": "x", "date": "d"},
    }
    with pytest.raises(GuardEvalError):
        load_manifest(_write(tmp_path / "d.json", manifest))
    manifest["inputs"][0]["human_annotation"] = {
        "lexical_expected": "accept", "semantic": "no-safety-issue-apparent",
        "reviewer": {"identity": None, "date": "d"},
    }
    with pytest.raises(GuardEvalError):
        load_manifest(_write(tmp_path / "e.json", manifest))


def test_captured_outputs_load_and_missing_fails(tmp_path):
    outdir = tmp_path / "caps"
    outdir.mkdir()
    (outdir / "TB-T1.json").write_text(json.dumps(_valid_output()), encoding="utf-8")
    captured = load_captured_outputs(outdir, ["TB-T1"])
    assert set(captured) == {"TB-T1"}
    with pytest.raises(GuardEvalError, match="No captured outputs"):
        load_captured_outputs(outdir, ["TB-T1", "TB-ABSENT"])


def test_secret_shaped_captures_refused(tmp_path):
    outdir = tmp_path / "caps"
    outdir.mkdir()
    evil = _valid_output(summary="Contact sk-abcdef1234567890 for help.")
    (outdir / "TB-T1.json").write_text(json.dumps(evil), encoding="utf-8")
    with pytest.raises(GuardEvalError, match="secret shape"):
        load_captured_outputs(outdir, ["TB-T1"])


def test_measure_scores_annotated_and_lists_pending():
    manifest = _manifest()
    results = measure_track_b(manifest, {"TB-T1": _valid_output()})
    assert results["n_inputs"] == 1
    assert results["n_annotated"] == 1
    assert results["n_pending_review"] == 0
    assert results["confusion"]["tn_accept"] == 1
    assert results["per_input"][0]["lexical_match"] is True


def test_measure_marks_unannotated_pending():
    results = measure_track_b(_manifest(annotated=False), {})
    assert results["n_annotated"] == 0
    assert results["pending_review_ids"] == ["TB-T1"]
    assert results["confusion"]["n_scored"] == 0


def test_measure_rejected_unsafe_counts_tp():
    manifest = _manifest()
    manifest["inputs"][0]["human_annotation"]["lexical_expected"] = "reject"
    manifest["inputs"][0]["human_annotation"]["semantic"] = "unsafe-recommendation"
    captured = {"TB-T1": _valid_output(
        recommended_actions=["Wipe every workstation tonight."])}
    results = measure_track_b(manifest, captured)
    assert results["confusion"]["tp_reject"] == 1


def test_measure_is_deterministic():
    manifest = _manifest()
    captured = {"TB-T1": _valid_output()}
    assert (measure_track_b(copy.deepcopy(manifest), dict(captured))
            == measure_track_b(manifest, captured))


def test_readiness_reports_blockers_without_secrets():
    blocked = readiness(provider_slug="openai", key_present=False,
                        opt_in=False, manifest_ok=True)
    assert blocked["ready"] is False
    assert len(blocked["blockers"]) == 2
    assert "provider" in blocked and "sk-" not in json.dumps(blocked)
    ready = readiness(provider_slug="openai", key_present=True,
                      opt_in=True, manifest_ok=True)
    assert ready == {"ready": True, "provider": "openai", "blockers": []}
    bad_provider = readiness(provider_slug="other", key_present=True,
                             opt_in=True, manifest_ok=True)
    assert bad_provider["ready"] is False


def test_shipped_manifest_is_valid_and_unannotated():
    from pathlib import Path
    manifest = load_manifest(
        Path(__file__).parent.parent / "fixtures" / "llm_guard_track_b_manifest_v1.json")
    assert len(manifest["inputs"]) == 4
    assert all(e["human_annotation"] is None for e in manifest["inputs"])
    results = measure_track_b(manifest, {})
    assert results["n_annotated"] == 0
    assert results["n_pending_review"] == 4
