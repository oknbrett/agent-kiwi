"""The coach digest leads with the recommendation and ranks by urgency.

These test the deterministic parts of the coach channel — ranking and rendering
— plus the orchestration in build_digest, using a stub agent so no LLM is
needed. The single most important property: an escalation always sorts above a
monitor, which sorts above routine, regardless of input order.
"""

from __future__ import annotations

from kiwi.coach import build_digest, rank_escalations, render_digest
from kiwi.domain import Client, Escalation, Observation

TODAY = "2026-06-07"


def _esc(client_id, decision, reason, action=""):
    return Escalation(client_id=client_id, date=TODAY, decision=decision,
                      reason=reason, recommended_action=action, source_text="")


def test_rank_puts_escalate_above_monitor_above_none():
    out = rank_escalations([
        _esc("a", "monitor", "m"),
        _esc("b", "escalate", "e"),
        _esc("c", "none", "n"),
    ])
    assert [e.decision for e in out] == ["escalate", "monitor", "none"]


def test_render_leads_with_action_needed():
    text = render_digest(
        _digest([
            _esc("sofia", "escalate", "sharp post-surgical knee pain",
                 "Pause leg work; advise Sofia see her physio."),
            _esc("tom", "monitor", "shoulder niggle, watch for recurrence"),
        ], ["Maya: On track — no action needed."])
    )
    lines = text.split("\n")
    action_idx = lines.index("ACTION NEEDED:")
    eye_idx = lines.index("KEEPING AN EYE ON:")
    else_idx = lines.index("EVERYONE ELSE:")
    # Action leads, then watch, then the routine summaries.
    assert action_idx < eye_idx < else_idx
    assert "physio" in text
    assert "Maya" in text


def _digest(escalations, summaries):
    from kiwi.domain import CoachDigest
    return CoachDigest(date=TODAY, escalations=escalations, summaries=summaries)


# ── build_digest orchestration, with a stub agent (no LLM) ─────────────────────


class StubAgent:
    """Returns a canned triage verdict per observation text, and canned summaries."""

    def __init__(self, verdicts, summaries):
        self._verdicts = verdicts  # obs.text -> Escalation
        self._summaries = summaries  # client.id -> str
        self.triaged = []

    def triage(self, client, obs):
        self.triaged.append((client.id, obs.text))
        return self._verdicts[obs.text]

    def summarize_for_coach(self, client, today):
        return self._summaries.get(client.id, "")


def test_build_digest_collects_and_ranks_across_clients():
    sofia = Client(id="sofia", name="Sofia", goal="post-ACL return")
    maya = Client(id="maya", name="Maya", goal="marathon")

    obs = {
        "sofia": [Observation("sofia", TODAY, "client_message", "knee gives out")],
        "maya": [Observation("maya", TODAY, "client_message", "legs wrecked")],
    }
    agent = StubAgent(
        verdicts={
            "knee gives out": _esc("sofia", "escalate", "instability", "see physio"),
            "legs wrecked": _esc("maya", "none", "DOMS"),
        },
        summaries={"sofia": "Check in — knee instability flagged.", "maya": "On track."},
    )

    digest = build_digest(agent, [sofia, maya], obs, TODAY)

    # Only the real escalation made the escalations list; routine 'none' did not.
    assert [e.client_id for e in digest.escalations] == ["sofia"]
    # Both clients got a one-line summary, prefixed with their name.
    assert any(s.startswith("Sofia:") for s in digest.summaries)
    assert any(s.startswith("Maya:") for s in digest.summaries)
