"""Agent Kiwi — domain contracts.

Kiwi is an AI coach-assistant for a solo personal trainer ("the coach").
Everything is organised around a single isolation root: the **client**.
A client is the analogue of a tenant/project in a production multi-tenant
agent — every piece of memory, every observation, every escalation is scoped
to exactly one client and must never leak across clients.

These are plain, typed dataclasses. No framework, no I/O — just the shapes the
rest of the system passes around, so each layer is testable in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal, Optional

# ── Clients ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Client:
    """A person the coach trains. The isolation root for all memory."""

    id: str
    name: str
    goal: str  # e.g. "Marathon in 12 weeks"
    notes: str = ""  # static context the coach knows up front (injury history, etc.)


# ── Observations ──────────────────────────────────────────────────────────────
# A raw, dated signal from or about a client — the input to the agent. In a
# real deployment these arrive over chat / app check-ins; here they are seeded.

ObservationSource = Literal["client_message", "app_metric", "coach_note"]


@dataclass(frozen=True)
class Observation:
    client_id: str
    date: str  # YYYY-MM-DD
    source: ObservationSource
    text: str


# ── Escalations ───────────────────────────────────────────────────────────────
# When Kiwi decides something needs the human coach, it produces one of these.
# `decision` mirrors the escalate-when-uncertain rule: monitor is the middle
# tier, none means routine.

EscalationDecision = Literal["escalate", "monitor", "none"]


@dataclass(frozen=True)
class Escalation:
    client_id: str
    date: str
    decision: EscalationDecision
    reason: str  # one line: why this decision
    recommended_action: str = ""  # what the coach should do (only when escalating)
    source_text: str = ""  # the observation text this judged


# ── Coach digest ──────────────────────────────────────────────────────────────
# The end-of-day report Kiwi writes to the human. Recommendation-first:
# escalations lead, routine summaries follow.


@dataclass
class CoachDigest:
    date: str
    escalations: list[Escalation] = field(default_factory=list)
    summaries: list[str] = field(default_factory=list)  # per-client one-liners

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "escalations": [asdict(e) for e in self.escalations],
            "summaries": list(self.summaries),
        }


def severity_rank(decision: EscalationDecision) -> int:
    """Higher = more urgent. Used to order the coach digest."""
    return {"escalate": 2, "monitor": 1, "none": 0}[decision]
