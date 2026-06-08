"""Coach channel — the human-in-the-loop interface.

Kiwi never acts on a health risk itself; it routes to the human coach. This
module assembles that routing into one **recommendation-first** end-of-day
digest: the things the coach must act on lead, the routine "all fine" lines
follow. The ranking is deterministic and pure (testable without an LLM); the
text inside each line is what the agent produced.

This mirrors the digest pattern from the production system: lead with the
recommendation, because a coach scanning ten clients in the morning should see
"check in with Sofia" before they see "Maya is on track".
"""

from __future__ import annotations

from typing import Mapping, Sequence

from .agent import KiwiAgent
from .domain import Client, CoachDigest, Escalation, Observation, severity_rank


def build_digest(
    agent: KiwiAgent,
    clients: Sequence[Client],
    observations: Mapping[str, Sequence[Observation]],
    sim_date: str,
) -> CoachDigest:
    """Triage every client's day and assemble the ranked coach digest.

    For each client: triage today's observations (escalations are recorded to
    that client's memory) and write a one-line summary. Escalations across all
    clients are then ranked most-urgent-first.
    """
    escalations: list[Escalation] = []
    summaries: list[str] = []

    for client in clients:
        for obs in observations.get(client.id, []):
            esc = agent.triage(client, obs)
            if esc.decision != "none":
                escalations.append(esc)
        summary = agent.summarize_for_coach(client, sim_date)
        if summary:
            summaries.append(f"{client.name}: {summary}")

    escalations.sort(key=lambda e: severity_rank(e.decision), reverse=True)
    return CoachDigest(date=sim_date, escalations=escalations, summaries=summaries)


def rank_escalations(escalations: Sequence[Escalation]) -> list[Escalation]:
    """Pure helper: most-urgent-first ordering. Stable within a tier."""
    return sorted(escalations, key=lambda e: severity_rank(e.decision), reverse=True)


def render_digest(digest: CoachDigest) -> str:
    """Plain-text rendering for the terminal / a coach's morning message."""
    lines = [f"Coach digest — {digest.date}", "=" * 40]

    act = [e for e in digest.escalations if e.decision == "escalate"]
    watch = [e for e in digest.escalations if e.decision == "monitor"]

    if act:
        lines.append("\nACTION NEEDED:")
        for e in act:
            lines.append(f"  ⚠ {e.reason}")
            if e.recommended_action:
                lines.append(f"      → {e.recommended_action}")
            if e.source_text:
                lines.append(f"      (client said: \"{e.source_text}\")")
    else:
        lines.append("\nNo escalations today.")

    if watch:
        lines.append("\nKEEPING AN EYE ON:")
        for e in watch:
            lines.append(f"  • {e.reason}")

    if digest.summaries:
        lines.append("\nEVERYONE ELSE:")
        for s in digest.summaries:
            lines.append(f"  - {s}")

    return "\n".join(lines)
