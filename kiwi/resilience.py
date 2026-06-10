"""Resilience and observability for the model calls.

A demo calls the model once and hopes. In production the call fails for boring,
transient reasons: the model is overloaded (HTTP 529), you hit a rate limit
(429), a connection blips. None of those mean "broken" — they mean "try again in
a moment". This module wraps a model call so the agent:

  - retries transient failures with exponential backoff + jitter, and
  - emits a structured JSON-lines trace of every attempt, so a run can be
    replayed when something goes wrong in production.

Deliberately dependency-free (no `anthropic` import): retryability is detected
by duck-typing the exception, so the whole thing is unit-tested with a fake
callable and no network — the same testing seam as the rest of Kiwi.
"""

from __future__ import annotations

import json
import logging
import random
import time
from typing import Any, Callable, Optional

# Transient HTTP statuses worth retrying. 529 is Anthropic's "overloaded".
RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 529}
_RETRYABLE_NAME_HINTS = ("timeout", "connection", "overloaded", "unavailable")

MAX_ATTEMPTS = 4  # 1 initial try + 3 retries
BASE_DELAY = 0.5  # seconds; the wait doubles each retry
CAP_DELAY = 8.0  # never wait longer than this between tries

logger = logging.getLogger("kiwi")


def is_retryable(exc: BaseException) -> bool:
    """True for transient faults (overload, rate limit, network), not for bugs.

    Duck-typed on purpose: a 400 (bad request) is *our* fault and must NOT be
    retried — retrying it just burns money and time re-sending the same broken
    call. We only retry things that might succeed if we simply wait.
    """
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(exc, "status", None)
    if isinstance(status, int) and status in RETRYABLE_STATUS:
        return True
    name = type(exc).__name__.lower()
    return any(hint in name for hint in _RETRYABLE_NAME_HINTS)


def backoff_delay(
    attempt: int, *, base: float = BASE_DELAY, cap: float = CAP_DELAY, jitter: float = 0.0
) -> float:
    """Exponential backoff for retry number `attempt` (0-based), capped.

    attempt 0 -> base, 1 -> 2*base, 2 -> 4*base ... never above `cap`. `jitter`
    (seconds) is added so a thundering herd of agents don't all retry in
    lockstep and re-spike the overloaded service.
    """
    raw = min(cap, base * (2**attempt))
    return raw + jitter


def call_with_retry(
    fn: Callable[[], Any],
    *,
    max_attempts: int = MAX_ATTEMPTS,
    base: float = BASE_DELAY,
    cap: float = CAP_DELAY,
    sleep: Callable[[float], None] = time.sleep,
    rng: Callable[[], float] = random.random,
    on_event: Optional[Callable[[dict], None]] = None,
) -> Any:
    """Call `fn`, retrying transient failures with exponential backoff.

    `sleep` and `rng` are injected so tests run instantly and deterministically.
    Every attempt emits an event via `on_event` (latency, outcome, and whether
    it will retry) so the structured trace can show exactly what happened.
    """
    for attempt in range(max_attempts):
        started = time.monotonic()
        try:
            result = fn()
        except BaseException as exc:
            latency_ms = round((time.monotonic() - started) * 1000, 1)
            is_last = attempt == max_attempts - 1
            will_retry = is_retryable(exc) and not is_last
            if on_event:
                on_event(
                    {
                        "phase": "attempt",
                        "attempt": attempt,
                        "latency_ms": latency_ms,
                        "outcome": "error",
                        "error": f"{type(exc).__name__}: {exc}",
                        "will_retry": will_retry,
                    }
                )
            if not will_retry:
                raise
            sleep(backoff_delay(attempt, base=base, cap=cap, jitter=base * rng()))
            continue

        latency_ms = round((time.monotonic() - started) * 1000, 1)
        if on_event:
            on_event(
                {
                    "phase": "attempt",
                    "attempt": attempt,
                    "latency_ms": latency_ms,
                    "outcome": "ok",
                }
            )
        return result

    raise RuntimeError("call_with_retry exhausted without returning")  # pragma: no cover


# ── Structured trace ──────────────────────────────────────────────────────────


class CallTrace:
    """A per-invocation structured trace.

    Tags every event with the channel + client it belongs to and emits it as a
    JSON line through the `kiwi` logger (or a custom sink, for tests). The
    collected `events` list is also kept in memory so the caller can introspect
    a single run without parsing logs.
    """

    def __init__(
        self,
        channel: str,
        client_id: str = "",
        emit: Optional[Callable[[dict], None]] = None,
    ) -> None:
        self.channel = channel
        self.client_id = client_id
        self._emit = emit or _emit_json
        self.events: list[dict] = []

    def record(self, **fields: Any) -> None:
        event = {"channel": self.channel, "client_id": self.client_id, **fields}
        self.events.append(event)
        self._emit(event)


def _emit_json(event: dict) -> None:
    logger.info(json.dumps(event, default=str))


def configure_logging(level: int = logging.INFO) -> None:
    """Opt-in: print the JSON-lines trace to stderr.

    Applications call this; importing the library does not configure logging
    (libraries shouldn't touch the root logger or attach handlers by surprise).
    """
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(level)
