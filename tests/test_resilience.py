"""The resilience layer is pure and testable without a network.

Retry/backoff is the difference between a demo (calls the model once and
crashes on a hiccup) and a product (survives a transient overload). Because
`call_with_retry` injects its `sleep` and `rng`, these tests assert the exact
retry behaviour and backoff schedule instantly and deterministically — no real
waiting, no API key, no flakiness.
"""

from __future__ import annotations

import pytest

from kiwi.resilience import CallTrace, backoff_delay, call_with_retry, is_retryable


# ── Fakes: exceptions that look like the SDK's, without importing it ───────────


class _HttpError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"http {status_code}")
        self.status_code = status_code


class _OverloadedError(Exception):  # detected by name, not status
    pass


# ── is_retryable ──────────────────────────────────────────────────────────────


def test_retryable_by_status_code():
    assert is_retryable(_HttpError(529))  # Anthropic overloaded
    assert is_retryable(_HttpError(429))  # rate limited
    assert is_retryable(_HttpError(503))  # service unavailable


def test_not_retryable_for_client_errors():
    # A 400/404 is our fault — retrying just re-sends a broken request.
    assert not is_retryable(_HttpError(400))
    assert not is_retryable(_HttpError(404))
    assert not is_retryable(ValueError("bad input"))


def test_retryable_by_exception_name():
    assert is_retryable(_OverloadedError())


# ── backoff schedule ──────────────────────────────────────────────────────────


def test_backoff_is_exponential_and_capped():
    assert backoff_delay(0, base=0.5, cap=8.0) == 0.5
    assert backoff_delay(1, base=0.5, cap=8.0) == 1.0
    assert backoff_delay(2, base=0.5, cap=8.0) == 2.0
    assert backoff_delay(3, base=0.5, cap=8.0) == 4.0
    assert backoff_delay(10, base=0.5, cap=8.0) == 8.0  # capped, not 512


# ── call_with_retry ───────────────────────────────────────────────────────────


def test_retries_transient_then_succeeds():
    attempts = {"n": 0}
    slept: list[float] = []

    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise _HttpError(529)  # overloaded twice, then recovers
        return "ok"

    events: list[dict] = []
    result = call_with_retry(
        flaky, sleep=slept.append, rng=lambda: 0.0, on_event=events.append
    )

    assert result == "ok"
    assert attempts["n"] == 3  # 2 failures + 1 success
    assert slept == [0.5, 1.0]  # exponential backoff, jitter zeroed for the test
    assert [e["outcome"] for e in events] == ["error", "error", "ok"]


def test_gives_up_after_max_attempts_and_reraises():
    def always_overloaded():
        raise _HttpError(503)

    events: list[dict] = []
    with pytest.raises(_HttpError):
        call_with_retry(
            always_overloaded,
            max_attempts=3,
            sleep=lambda d: None,
            rng=lambda: 0.0,
            on_event=events.append,
        )

    assert len(events) == 3  # tried three times
    assert events[-1]["will_retry"] is False  # the last one gave up


def test_non_retryable_fails_fast_without_sleeping():
    attempts = {"n": 0}
    slept: list[float] = []

    def bad_request():
        attempts["n"] += 1
        raise _HttpError(400)

    with pytest.raises(_HttpError):
        call_with_retry(bad_request, sleep=slept.append)

    assert attempts["n"] == 1  # no retry on a client error
    assert slept == []  # and no backoff wait


# ── CallTrace ─────────────────────────────────────────────────────────────────


def test_call_trace_tags_events_and_collects_them():
    sink: list[dict] = []
    trace = CallTrace("triage", "sofia", emit=sink.append)

    trace.record(phase="attempt", attempt=0, outcome="ok")
    trace.record(phase="response", stop_reason="end_turn")

    assert len(trace.events) == 2
    assert all(e["channel"] == "triage" and e["client_id"] == "sofia" for e in trace.events)
    assert sink == trace.events  # every recorded event was emitted to the sink
