"""Agent Kiwi — the agent loop.

This is the part that actually talks to a model. It is a *real* agent, not a
prompt wrapper: it runs a manual tool-use loop, it loads its own instructions on
demand via progressive disclosure, and it persists what it learns to a
per-client memory journal.

Three entry points, one loop underneath:
  triage(client, obs)            — is this observation a health risk the coach
                                   must see? Forces the flag-health-risk skill
                                   and returns a structured Escalation.
  daily_run(client, obs, date)   — the autonomous touchpoint: read memory, write
                                   a grounded check-in, optionally remember
                                   something new.
  chat(client, message)          — on-demand reply to a client message.

Progressive disclosure is the whole architecture:
  - Level 1 (always in context): the skill *catalog* — name + one-line
    description per skill (~tens of tokens each).
  - Level 2 (loaded on trigger): the full SKILL.md body, fetched only when the
    model calls the `use_skill` tool. The bulk of the instruction tokens stay
    out of context until the moment they're needed.

The model never sees another client's memory: every prompt is assembled from
`MemoryStore.context_for(client_id, today)`, which is single-client by
construction (see memory.py and tests/test_memory_isolation.py).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Optional

from .domain import Client, Escalation, Observation
from .memory import MemoryEntry, MemoryStore, author_entry
from .resilience import CallTrace, call_with_retry
from .skill_loader import (
    SkillMeta,
    discover_skills,
    load_skill_body,
    render_skill_catalog,
)

# ── Models ────────────────────────────────────────────────────────────────────
# The loop runs on Sonnet (good tool-use + cost). Swap here, not at call sites.
LOOP_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024
MAX_TOOL_TURNS = 6  # safety bound on the agentic loop

# The one tool the agent has: pull a skill body into context on demand.
USE_SKILL_TOOL: dict[str, Any] = {
    "name": "use_skill",
    "description": (
        "Load the full instructions for one of the available skills. Call this "
        "with the skill's name the moment a task matches it — the catalog only "
        "gives you the name and a one-line description; the actual procedure "
        "lives in the skill body you load here."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "The exact skill name from the catalog.",
            }
        },
        "required": ["name"],
    },
}

_ROLE = (
    "You are Kiwi, the assistant to a solo personal trainer (\"the coach\"). You "
    "help the coach look after their clients: you triage what clients report, you "
    "send grounded daily check-ins, and you decide what the human coach needs to "
    "see. You are not a doctor and you do not diagnose — when something might be a "
    "real health risk, your job is to route it to the human, not to handle it.\n\n"
    "You work skill-first. Below is a catalog of skills. Each one is a focused "
    "procedure. When a task matches a skill, call the `use_skill` tool to load "
    "its full instructions, then follow them exactly — including the required "
    "output format. Do not improvise a procedure a skill already defines."
)


def _system_blocks(catalog: str) -> list[dict[str, Any]]:
    """Stable system prefix, marked cacheable.

    Role + skill catalog don't change between calls, so they form a clean prompt
    prefix. The volatile per-client context goes in the user turn, after this
    cached block, so the cache prefix stays valid across clients and days.
    """
    return [
        {
            "type": "text",
            "text": f"{_ROLE}\n\n{catalog}",
            "cache_control": {"type": "ephemeral"},
        }
    ]


def _as_str_list(value: Any) -> list[str]:
    """Defensive coercion for model-produced id lists (drop non-strings)."""
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, str)]


def _extract_json(text: str) -> Optional[dict]:
    """Pull the first JSON object out of a model reply (handles ```json fences)."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        candidate = brace.group(0) if brace else None
    if candidate is None:
        return None
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


@dataclass
class ChatResult:
    text: str
    memory_note: str = ""


class KiwiAgent:
    """The agent. Holds the memory store, the skill catalog, and the LLM client."""

    def __init__(
        self,
        memory: Optional[MemoryStore] = None,
        *,
        skills: Optional[list[SkillMeta]] = None,
        client: Any = None,
    ) -> None:
        self.memory = memory or MemoryStore()
        self.skills = skills if skills is not None else discover_skills()
        self.catalog = render_skill_catalog(self.skills)
        self._client = client  # injectable for tests; real one is created lazily
        self.last_trace: list[dict] = []  # events from the most recent _run_loop

    # ── LLM plumbing ──────────────────────────────────────────────────────────

    def _anthropic(self) -> Any:
        if self._client is not None:
            return self._client
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Export it to run the live agent, "
                "or inject a fake client (KiwiAgent(client=...)) for offline use."
            )
        import anthropic  # imported lazily so the pure modules don't need the SDK

        self._client = anthropic.Anthropic()
        return self._client

    def _run_loop(
        self,
        user_content: str,
        *,
        force_skill: Optional[str] = None,
        channel: str = "loop",
        client_id: str = "",
    ) -> str:
        """Run the manual tool-use loop until the model stops calling tools.

        If force_skill is set, the first turn is forced to call `use_skill` so a
        triage call can't skip its skill. After that the loop is model-driven.

        Every model call goes through `call_with_retry`, so a transient overload
        or rate-limit is retried with backoff instead of crashing the run, and a
        `CallTrace` records each attempt for replay (see resilience.py).
        """
        client = self._anthropic()
        system = _system_blocks(self.catalog)
        messages: list[dict[str, Any]] = [{"role": "user", "content": user_content}]
        trace = CallTrace(channel, client_id)
        self.last_trace = trace.events

        final_text = ""
        for turn in range(MAX_TOOL_TURNS):
            kwargs: dict[str, Any] = {
                "model": LOOP_MODEL,
                "max_tokens": MAX_TOKENS,
                "system": system,
                "tools": [USE_SKILL_TOOL],
                "messages": messages,
            }
            if turn == 0 and force_skill:
                kwargs["tool_choice"] = {"type": "tool", "name": "use_skill"}

            resp = call_with_retry(
                lambda kw=kwargs: client.messages.create(**kw),
                on_event=lambda e, t=turn: trace.record(turn=t, **e),
            )
            usage = getattr(resp, "usage", None)
            trace.record(
                phase="response",
                turn=turn,
                stop_reason=getattr(resp, "stop_reason", None),
                input_tokens=getattr(usage, "input_tokens", None),
                output_tokens=getattr(usage, "output_tokens", None),
            )
            # Preserve the full content (incl. any tool_use blocks) for the next turn.
            messages.append({"role": "assistant", "content": resp.content})

            if resp.stop_reason == "tool_use":
                results = []
                for block in resp.content:
                    if getattr(block, "type", None) == "tool_use" and block.name == "use_skill":
                        try:
                            body = load_skill_body(block.input["name"])
                        except KeyError:
                            body = (
                                f"No skill named {block.input.get('name')!r}. "
                                f"Available: {', '.join(m.name for m in self.skills)}."
                            )
                        results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": body,
                            }
                        )
                messages.append({"role": "user", "content": results})
                continue

            # stop_reason == "end_turn" (or any non-tool stop): collect the text.
            final_text = "".join(
                b.text for b in resp.content if getattr(b, "type", None) == "text"
            )
            break

        return final_text

    # ── Entry points ──────────────────────────────────────────────────────────

    def triage(self, client: Client, obs: Observation) -> Escalation:
        """Decide whether an observation needs the human coach. Records the verdict."""
        memory_ctx = self.memory.context_for(client.id, obs.date)
        user = (
            f"Triage this observation about {client.name} "
            f"(goal: {client.goal}).\n"
            f"What the coach already knows: {client.notes or '(nothing on file)'}\n\n"
            f"Memory for this client:\n{memory_ctx}\n\n"
            f"Observation [{obs.date} · {obs.source}]: {obs.text}\n\n"
            "Use the flag-health-risk skill and return its JSON verdict only."
        )
        raw = self._run_loop(
            user, force_skill="flag-health-risk", channel="triage", client_id=client.id
        )
        data = _extract_json(raw) or {}
        decision = data.get("decision")
        if decision not in ("escalate", "monitor", "none"):
            # An unreadable verdict is maximal uncertainty, and the triage rule
            # is asymmetric on purpose: when uncertain, fail toward the human.
            # A parse failure must surface as "look at this", not vanish into
            # the monitor tier — the catastrophic case is a real risk silently
            # downgraded by a formatting bug.
            return self._escalate_unreadable(client, obs)
        esc = Escalation(
            client_id=client.id,
            date=obs.date,
            decision=decision,  # type: ignore[arg-type]
            reason=data.get("reason", "").strip(),
            recommended_action=data.get("recommended_action", "").strip(),
            source_text=obs.text,
        )
        self._record_triage(client, esc)
        return esc

    def _escalate_unreadable(self, client: Client, obs: Observation) -> Escalation:
        """The triage verdict could not be parsed — route to the human."""
        esc = Escalation(
            client_id=client.id,
            date=obs.date,
            decision="escalate",
            reason="Triage produced no readable verdict — escalating by policy, not by judgement.",
            recommended_action="Read the observation yourself; the agent could not classify it.",
            source_text=obs.text,
        )
        self._record_triage(client, esc)
        return esc

    def _record_triage(self, client: Client, esc: Escalation) -> None:
        """Persist a decision so future runs (and reflection) can see the history."""
        if esc.decision == "none":
            return  # routine — not worth a memory entry
        entry = author_entry(
            body=f"{esc.decision.upper()}: {esc.reason}".strip(": "),
            type="escalation_decision",
            today=esc.date,
            subject=client.name,
            item=esc.decision,
        )
        self.memory.add(client.id, entry)

    def daily_run(
        self, client: Client, observations: list[Observation], sim_date: str
    ) -> ChatResult:
        """Autonomous daily touchpoint: triage, check in, reconcile the memory."""
        # 1. Triage everything that came in today (escalations get recorded).
        for obs in observations:
            self.triage(client, obs)

        # 2. Write a grounded check-in via the daily-checkin skill. The prompt
        #    includes the client's observations with ids so the model can name
        #    which ones today's evidence confirms or contradicts.
        memory_ctx = self.memory.context_for(client.id, sim_date)
        review = self.memory.observations_for_review(client.id, sim_date)
        recent = "\n".join(f"- [{o.date} · {o.source}] {o.text}" for o in observations)
        user = (
            f"Run today's check-in for {client.name} (goal: {client.goal}). "
            f"Today is {sim_date}.\n"
            f"What the coach knows: {client.notes or '(nothing on file)'}\n\n"
            f"Memory for this client:\n{memory_ctx}\n\n"
            + (f"{review}\n\n" if review else "")
            + f"What came in today:\n{recent or '(nothing today)'}\n\n"
            "Use the daily-checkin skill and return its JSON only."
        )
        raw = self._run_loop(
            user, force_skill="daily-checkin", channel="daily", client_id=client.id
        )
        data = _extract_json(raw) or {}

        # 3. Apply the evidence verdicts: confirmation nudges confidence up,
        #    contradiction pulls it down 2x. This is what makes stale beliefs
        #    fade instead of living forever (see memory.next_confidence).
        self.memory.apply_evidence(
            client.id,
            confirmed=_as_str_list(data.get("confirmed")),
            contradicted=_as_str_list(data.get("contradicted")),
        )

        # 4. Persist anything new the model judged worth remembering. The
        #    trigger is mandatory for observations (validate_entry enforces it),
        #    so a note without one is dropped, not saved degraded.
        note = (data.get("memory_note") or "").strip()
        trigger = (data.get("note_trigger") or "").strip()
        if note and trigger:
            self.memory.add(
                client.id,
                author_entry(
                    body=note,
                    type="observation",
                    today=sim_date,
                    subject=client.name,
                    trigger=trigger,
                ),
            )

        result = ChatResult(text=data.get("message", "").strip(), memory_note=note)
        self.memory.compact(client.id, sim_date)
        return result

    def summarize_for_coach(self, client: Client, today: str) -> str:
        """One recommendation-first line about this client for the coach digest."""
        memory_ctx = self.memory.context_for(client.id, today)
        user = (
            f"Summarize {client.name} (goal: {client.goal}) for the coach's "
            f"end-of-day digest. Today is {today}.\n"
            f"What the coach knows: {client.notes or '(nothing on file)'}\n\n"
            f"Memory for this client:\n{memory_ctx}\n\n"
            "Use the summarize-for-coach skill and return its JSON only."
        )
        raw = self._run_loop(
            user, force_skill="summarize-for-coach", channel="summarize", client_id=client.id
        )
        data = _extract_json(raw) or {}
        return data.get("summary", "").strip()

    def chat(self, client: Client, message: str, today: str) -> str:
        """On-demand reply to a client message, grounded in their memory."""
        memory_ctx = self.memory.context_for(client.id, today)
        user = (
            f"{client.name} (goal: {client.goal}) sent a message. Today is {today}.\n"
            f"What the coach knows: {client.notes or '(nothing on file)'}\n\n"
            f"Memory for this client:\n{memory_ctx}\n\n"
            f"Message: {message}\n\n"
            "Reply as the coach's assistant. Reach for a skill if one fits."
        )
        return self._run_loop(user, channel="chat", client_id=client.id)
