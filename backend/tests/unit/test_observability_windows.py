"""P1-21 tests: rolling-window metrics (DI-015) and latency tails (DI-016).

Deterministic via injected monotonic timestamps — no wall-clock sleeps.
Lifetime counters keep their exact meanings; windows are recency views.
"""
import json
import threading

import pytest

from app.services import observability as obs


@pytest.fixture(autouse=True)
def _clean():
    obs.reset()
    yield
    obs.reset()


T0 = 1_000_000.0
W = obs.WINDOW_SECONDS


def test_window_counts_use_injected_clock(monkeypatch):
    times = iter([T0, T0 + 10, T0 + W + 20])
    monkeypatch.setattr(obs, "_now", lambda: next(times))
    obs.record_event(obs.RAG_QUERY_COMPLETED)  # t=T0
    obs.record_event(obs.RAG_QUERY_COMPLETED)  # t=T0+10
    snap = obs.get_snapshot()  # t=T0+W+20: both expired
    assert snap["window_events"] == {}
    assert snap["events"][obs.RAG_QUERY_COMPLETED][obs.CATEGORY_OK] == 2


def test_boundary_age_equals_window_is_expired(monkeypatch):
    monkeypatch.setattr(obs, "_now", lambda: T0 + W)
    obs.record_event(obs.RAG_QUERY_COMPLETED, now=T0)  # age exactly W
    snap = obs.get_snapshot()
    assert snap["window_events"] == {}
    assert snap["events"][obs.RAG_QUERY_COMPLETED][obs.CATEGORY_OK] == 1


def test_empty_window_is_unknown_not_healthy(monkeypatch):
    monkeypatch.setattr(obs, "_now", lambda: T0)
    obs.record_event(obs.RAG_QUERY_ATTEMPTED)
    obs.record_event(obs.RAG_QUERY_COMPLETED)
    monkeypatch.setattr(obs, "_now", lambda: T0 + W + 1)  # window drained
    report = obs.build_health_report(obs.get_snapshot())
    # Lifetime still ok; window has no recent observations -> unknown.
    assert report["indicators"]["rag_failure_rate"]["state"] == obs.STATE_OK
    assert report["indicators"]["rag_failure_rate_window"]["state"] == obs.STATE_UNKNOWN
    assert report["indicators"]["rag_failure_rate_window"]["rate"] is None
    assert report["state"] == obs.STATE_OK


def test_window_distinguishes_no_recent_from_zero_failures(monkeypatch):
    monkeypatch.setattr(obs, "_now", lambda: T0)
    obs.record_event(obs.RAG_QUERY_ATTEMPTED)
    obs.record_event(obs.RAG_QUERY_COMPLETED)  # window: 1 attempt, 0 failures
    report = obs.build_health_report(obs.get_snapshot())
    window = report["indicators"]["rag_failure_rate_window"]
    assert window == {"failures": 0, "attempts": 1, "rate": 0.0,
                      "state": obs.STATE_OK, "window_seconds": W}


def test_windowed_failure_detected(monkeypatch):
    monkeypatch.setattr(obs, "_now", lambda: T0)
    obs.record_event(obs.RAG_QUERY_ATTEMPTED)
    obs.record_event(obs.RAG_QUERY_FAILED, obs.CATEGORY_TIMEOUT)
    report = obs.build_health_report(obs.get_snapshot())
    window = report["indicators"]["rag_failure_rate_window"]
    assert window["failures"] == 1 and window["attempts"] == 1
    assert window["rate"] == pytest.approx(1.0)
    assert window["state"] == obs.STATE_DEGRADED
    assert report["state"] == obs.STATE_DEGRADED


def test_lifetime_totals_survive_expiry(monkeypatch):
    obs.record_event(obs.RAG_QUERY_ATTEMPTED, now=T0)
    obs.record_event(obs.RAG_QUERY_ATTEMPTED, now=T0)
    monkeypatch.setattr(obs, "_now", lambda: T0 + W + 5)
    snap = obs.get_snapshot()
    assert snap["events"][obs.RAG_QUERY_ATTEMPTED][obs.CATEGORY_OK] == 2
    assert snap["window_events"] == {}


def test_concurrent_window_updates_exact():
    errors = []

    def worker(n):
        try:
            for i in range(200):
                obs.record_event(obs.RAG_QUERY_COMPLETED, now=T0 + i)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(k,)) for k in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    snap = obs.get_snapshot()
    # Lifetime exact under the lock (stronger than the pre-existing
    # loss-tolerant assertion); window bounded by series cap.
    assert snap["events"][obs.RAG_QUERY_COMPLETED][obs.CATEGORY_OK] == 800


def test_latency_percentiles_on_deterministic_set():
    for v in [10.0, 20.0, 30.0, 40.0, 100.0]:
        obs.record_latency("rag.query", v, now=T0)
    stats = obs.get_snapshot()["latency_ms"]["rag.query"]
    assert stats["count"] == 5
    assert stats["mean"] == pytest.approx(40.0)
    assert stats["p50"] == pytest.approx(30.0)
    assert stats["p95"] == pytest.approx(88.0)  # linear interpolation: rank 3.8
    assert stats["max"] == pytest.approx(100.0)
    assert stats["unit"] == "ms"
    # Lifetime mean preserved alongside.
    assert obs.get_snapshot()["mean_latency_ms"]["rag.query"] == pytest.approx(40.0)


def test_latency_single_and_empty_samples():
    snap = obs.get_snapshot()
    assert "rag.query" not in snap["latency_ms"]
    obs.record_latency("rag.query", 7.5, now=T0)
    stats = obs.get_snapshot()["latency_ms"]["rag.query"]
    assert stats["count"] == 1
    assert stats["p50"] == stats["p95"] == stats["max"] == pytest.approx(7.5)
    report = obs.build_health_report(obs.get_snapshot())
    window = report["indicators"]["rag_query_latency_ms_window"]
    assert window["count"] == 1 and window["p95"] == pytest.approx(7.5)


def test_latency_expiry_and_lifetime_mean_kept(monkeypatch):
    monkeypatch.setattr(obs, "_now", lambda: T0)
    obs.record_latency("rag.query", 10.0)
    obs.record_latency("rag.query", 30.0)
    monkeypatch.setattr(obs, "_now", lambda: T0 + W + 1)
    obs.record_latency("rag.query", 50.0)
    snap = obs.get_snapshot()
    stats = snap["latency_ms"]["rag.query"]
    assert stats["count"] == 1  # only the recent sample in-window
    assert stats["max"] == pytest.approx(50.0)
    assert snap["mean_latency_ms"]["rag.query"] == pytest.approx(30.0)  # lifetime


def test_bad_latency_samples_ignored_not_counted():
    for bad in (float("nan"), float("inf"), -5.0, "slow", None):
        obs.record_latency("rag.query", bad, now=T0)
    snap = obs.get_snapshot()
    assert "rag.query" not in snap["latency_ms"]
    assert "rag.query" not in snap["mean_latency_ms"]


def test_window_buffers_are_bounded():
    for i in range(obs.WINDOW_SERIES_MAXLEN + 500):
        obs.record_event(obs.RAG_QUERY_COMPLETED, now=T0 + i * 0.001)
    total = sum(len(s) for cats in obs._window_events.values() for s in cats.values())
    assert total <= obs.WINDOW_SERIES_MAXLEN * len(obs._window_events)
    for i in range(obs.LATENCY_SAMPLE_MAXLEN + 200):
        obs.record_latency("rag.query", 1.0, now=T0)
    assert len(obs._latency_samples["rag.query"]) <= obs.LATENCY_SAMPLE_MAXLEN


def test_no_payloads_in_window_state():
    obs.record_event(obs.RAG_QUERY_COMPLETED, now=T0)
    obs.record_latency("rag.query", 12.5, now=T0)
    blob = json.dumps(obs.get_snapshot())
    for banned in ("secret", "sk-", "bearer", "traceback", "prompt"):
        assert banned not in blob.lower()
    # Only floats retained in buffers.
    for cats in obs._window_events.values():
        for series in cats.values():
            assert all(isinstance(t, float) for t in series)
    for samples in obs._latency_samples.values():
        assert all(isinstance(t, float) and isinstance(v, float)
                   for t, v in samples)


def test_reset_clears_windows_and_buffers():
    obs.record_event(obs.RAG_QUERY_COMPLETED, now=T0)
    obs.record_latency("rag.query", 5.0, now=T0)
    obs.reset()
    snap = obs.get_snapshot()
    assert snap["events"] == {}
    assert snap["window_events"] == {}
    assert snap["latency_ms"] == {}
    assert snap["mean_latency_ms"] == {}


def test_old_shape_snapshots_still_report():
    report = obs.build_health_report({"events": {}, "mean_latency_ms": {}})
    assert report["indicators"]["rag_failure_rate_window"]["state"] == obs.STATE_UNKNOWN
    assert report["indicators"]["rag_query_latency_ms_window"]["count"] == 0
    assert report["state"] == obs.STATE_UNKNOWN
