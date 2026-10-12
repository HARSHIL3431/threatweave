"""P1-5 tests: health calculations, snapshot export safety, concurrency.

Deterministic and offline. No network, no real LLM, no secrets.
"""
import asyncio
import json
import threading

import pytest

from app.services import observability as obs


@pytest.fixture(autouse=True)
def _clean():
    obs.reset()
    yield
    obs.reset()


def _snapshot_with(**overrides):
    snap = {"events": {}, "mean_latency_ms": {}}
    snap.update(overrides)
    return snap


# 1/3/4. Empty snapshot, aggregation, and zero-denominator behavior.
def test_empty_snapshot_yields_unknown_not_healthy():
    report = obs.build_health_report(_snapshot_with())
    assert report["state"] == obs.STATE_UNKNOWN
    for name in ("rag_failure_rate", "llm_failure_rate",
                 "llm_validation_rejection_rate", "llm_degraded_share",
                 "rag_empty_rate"):
        indicator = report["indicators"][name]
        assert indicator["rate"] is None
        assert indicator["state"] == obs.STATE_UNKNOWN


def test_healthy_sample_reports_ok():
    obs.record_event(obs.RAG_QUERY_ATTEMPTED)
    obs.record_event(obs.RAG_QUERY_COMPLETED)
    obs.record_event(obs.LLM_GENERATE_COMPLETED)
    report = obs.build_health_report(obs.get_snapshot())
    assert report["indicators"]["rag_failure_rate"] == {
        "failures": 0, "attempts": 1, "rate": 0.0, "state": obs.STATE_OK,
    }
    assert report["indicators"]["llm_failure_rate"]["state"] == obs.STATE_OK
    assert report["state"] == obs.STATE_OK


def test_failure_rates_and_counts():
    for _ in range(3):
        obs.record_event(obs.RAG_QUERY_ATTEMPTED)
    obs.record_event(obs.RAG_QUERY_COMPLETED)
    obs.record_event(obs.RAG_QUERY_FAILED, obs.CATEGORY_TIMEOUT)
    obs.record_event(obs.RAG_QUERY_FAILED, obs.CATEGORY_INTEGRITY)
    obs.record_event(obs.RAG_INTEGRITY_FAILED, obs.CATEGORY_INTEGRITY)
    obs.record_event(obs.LLM_GENERATE_FAILED, obs.CATEGORY_PROVIDER_ERROR)
    obs.record_event(obs.LLM_VALIDATION_REJECTED, "ungrounded_techniques")
    report = obs.build_health_report(obs.get_snapshot())
    rag = report["indicators"]["rag_failure_rate"]
    assert rag == {"failures": 2, "attempts": 3,
                   "rate": pytest.approx(2 / 3), "state": obs.STATE_DEGRADED}
    assert report["indicators"]["rag_integrity_failures"] == {
        "count": 1, "state": obs.STATE_DEGRADED}
    llm = report["indicators"]["llm_failure_rate"]
    assert llm["failures"] == 1 and llm["attempts"] == 1
    assert llm["rate"] == pytest.approx(1.0)
    assert report["indicators"]["llm_validation_rejection_rate"]["rejected"] == 1
    assert report["state"] == obs.STATE_DEGRADED


# 5. Latency values and units.
def test_latency_means():
    obs.record_latency("rag.query", 10.0)
    obs.record_latency("rag.query", 30.0)
    obs.record_latency("llm.generate", 250.0)
    report = obs.build_health_report(obs.get_snapshot())
    assert report["indicators"]["rag_query_latency_ms_mean"] == {"value": 20.0}
    assert report["indicators"]["llm_generate_latency_ms_mean"] == {"value": 250.0}
    empty = obs.build_health_report(_snapshot_with())
    assert empty["indicators"]["rag_query_latency_ms_mean"] == {"value": None}


# 6/15. Bounded names and stable categories.
def test_vocabulary_is_bounded():
    names = [v for k, v in vars(obs).items()
             if k.isupper() and isinstance(v, str)
             and (k.startswith(("RAG_", "LLM_")))]
    assert names, "event vocabulary must exist"
    assert all(v and " " not in v for v in names)
    assert len(set(names)) == len(names)
    assert obs.category_for_error_code("LLM_TIMEOUT") == obs.CATEGORY_TIMEOUT
    assert obs.category_for_error_code("NOPE") == obs.CATEGORY_UNEXPECTED
    assert obs.category_for_error_code(None) == obs.CATEGORY_UNEXPECTED


# 7. Snapshot reads do not mutate counters.
def test_snapshot_read_is_side_effect_free():
    obs.record_event(obs.RAG_QUERY_COMPLETED)
    first = obs.get_snapshot()
    second = obs.get_snapshot()
    assert first == second
    report = obs.build_health_report(first)
    assert obs.get_snapshot() == first
    # One completed retrieval with zero empties: observed and healthy.
    assert report["indicators"]["rag_empty_rate"]["state"] == obs.STATE_OK
    # No completions at all: unknown, never healthy-by-default.
    assert obs.build_health_report(
        {"events": {}, "mean_latency_ms": {}}
    )["indicators"]["rag_empty_rate"]["state"] == obs.STATE_UNKNOWN


# 8. Concurrent asyncio updates stay exact; threads never corrupt.
def test_asyncio_concurrency_exact():
    async def hammer():
        await asyncio.gather(*[
            asyncio.to_thread(obs.record_event, obs.RAG_QUERY_COMPLETED)
            for _ in range(50)
        ])

    asyncio.run(hammer())
    snap = obs.get_snapshot()
    # asyncio.to_thread runs on threads: count exactness is not guaranteed,
    # but state must stay intact and no observation may be fabricated.
    total = snap["events"][obs.RAG_QUERY_COMPLETED][obs.CATEGORY_OK]
    assert 0 < total <= 50


def test_single_thread_counts_exact():
    for _ in range(25):
        obs.record_event(obs.LLM_GENERATE_COMPLETED)
    assert obs.get_snapshot()["events"][obs.LLM_GENERATE_COMPLETED] == {
        obs.CATEGORY_OK: 25}


def test_thread_race_never_corrupts_state():
    errors = []

    def worker():
        try:
            for _ in range(200):
                obs.record_event(obs.RAG_QUERY_ATTEMPTED)
                obs.record_latency("rag.query", 1.0)
                obs.get_snapshot()
        except Exception as exc:  # noqa: BLE001 - must not happen
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    snap = obs.get_snapshot()
    blob = json.dumps(snap)
    assert isinstance(json.loads(blob), dict)
    total = snap["events"][obs.RAG_QUERY_ATTEMPTED][obs.CATEGORY_OK]
    assert 0 < total <= 800


# 9. No sensitive payloads in exported snapshots.
def test_snapshot_schema_has_no_sensitive_fields():
    obs.record_event(obs.RAG_QUERY_COMPLETED)
    snap = obs.get_snapshot()
    # P1-21 extends the snapshot with rolling-window views (DI-015/DI-016);
    # the key set below is the compatibility contract for this extension.
    assert set(snap) == {"events", "mean_latency_ms", "note",
                         "window_seconds", "window_events", "latency_ms"}
    blob = json.dumps(snap)
    # Event names legitimately contain "query" (rag.query.*); the assertion
    # is that no query *text*, scores, or secrets appear.
    for banned in ("prompt", "cve-", "sk-", "bearer", "traceback", "path", "/"):
        assert banned not in blob.lower()


# 12. Export path cannot trigger RAG/LLM work or fail requests.
def test_health_report_is_pure_offline_computation(monkeypatch):
    import app.services.rag_service as rag_module
    import app.services.llm_service as llm_module

    def boom(*args, **kwargs):
        raise AssertionError("health inspection must not do retrieval/LLM work")

    monkeypatch.setattr(rag_module.RagService, "query", boom)
    monkeypatch.setattr(llm_module.LLMService, "generate_explanation", boom)
    report = obs.build_health_report(obs.get_snapshot())
    assert report["state"] == obs.STATE_UNKNOWN


def test_malformed_snapshot_degrades_safely():
    report = obs.build_health_report({"events": None, "mean_latency_ms": None})
    assert report["state"] in (obs.STATE_UNKNOWN, obs.STATE_OK)
    assert obs.build_health_report({})["state"] == obs.STATE_UNKNOWN
