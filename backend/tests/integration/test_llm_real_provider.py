"""Opt-in real-LLM end-to-end validation (Secure Groq phase).

Never runs in ordinary CI: skipped unless BOTH are set:
  THREATWEAVE_REAL_LLM_TEST=1  and  LLM_API_KEY=<funded key>

Exercises the real POST /api/v1/explain path with the project's supported
fixture flows (synthetic CICIDS feature vectors — no real traffic, IPs, PCAPs,
or credentials transmitted). Exactly two external requests per run
(benign + anomalous), no retries, bounded client timeout. A 401/429/malformed
provider response fails the test through the app's controlled error mapping —
it is never retried or masked.
No secret is printed, logged, or stored by these tests.
"""
import json
import os
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

NEED = os.environ.get("THREATWEAVE_REAL_LLM_TEST") == "1" and bool(
    os.environ.get("LLM_API_KEY")
)

pytestmark = pytest.mark.skipif(
    not NEED,
    reason="opt-in real-LLM test: set THREATWEAVE_REAL_LLM_TEST=1 and LLM_API_KEY",
)

_FIXTURES = json.loads(
    (Path(__file__).parent.parent / "fixtures" / "sample_flows.json").read_text()
)

_RETRIEVED_RE = re.compile(r"\[retrieved-not-confirmed\] (T[\d.]+)")


def _retrieved_ids(explain_body) -> set:
    return set(
        _RETRIEVED_RE.findall(
            " ".join(explain_body["attack_context"]["retrieved_context"])
        )
    )


def _assert_grounded(body):
    exp = body["explanation"]
    assert exp["summary"] and exp["summary"].strip()
    assert exp["anomaly_assessment"] and exp["anomaly_assessment"].strip()
    assert exp["limitations"]
    assert body["llm"]["provider"] == "openai"
    assert body["llm"]["validated"] is True
    assert body["llm"]["latency_ms"] > 0
    allowed = _retrieved_ids(body)
    for c in exp["potential_attack_context"]:
        assert c["technique_id"] in allowed, (
            f"ungrounded technique {c['technique_id']} not in retrieved {sorted(allowed)}"
        )
        assert c["confidence"] in ("low", "medium", "high")


def _explain(client: TestClient, flow: dict):
    r = client.post("/api/v1/explain", json={"flow": flow, "top_k": 3}, timeout=180.0)
    assert r.status_code == 200, f"explain failed: {r.status_code} {r.text[:300]}"
    return r.json()


@pytest.mark.parametrize("anomaly", [False, True])
def test_real_explain_fixture_grounded(monkeypatch, anomaly):
    # Point the request-scoped services at the real provider; the key itself
    # comes only from the explicitly provided environment (never from files).
    monkeypatch.setattr(settings, "RAG_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    flow = _FIXTURES["anomalous_flow" if anomaly else "benign_flow"]["input"]
    with TestClient(app) as client:
        body = _explain(client, flow)
    assert body["detection"]["is_anomaly"] is anomaly
    _assert_grounded(body)
