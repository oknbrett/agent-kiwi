"""The agent loop is testable without a network — by injecting a fake LLM.

A real agent has a non-deterministic core (the model), but the *machinery*
around it — the tool-use loop, skill loading, JSON parsing, memory writes — is
ordinary code and must be tested like ordinary code. These tests inject a
scripted fake client so we can assert the loop:
  - forces the flag-health-risk skill on a triage call,
  - actually loads the skill body and feeds it back as a tool_result,
  - parses the verdict into a structured Escalation,
  - records an escalation into the right client's memory and nowhere else.
"""

from __future__ import annotations

from kiwi.agent import KiwiAgent
from kiwi.domain import Client, Observation

TODAY = "2026-06-07"


# ── A minimal stand-in for the Anthropic SDK response shape ────────────────────


class _Block:
    def __init__(self, type, **kw):
        self.type = type
        for k, v in kw.items():
            setattr(self, k, v)


class _Resp:
    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason


class FakeClient:
    """Replays a scripted conversation and records the calls it received."""

    def __init__(self, script):
        self._script = list(script)
        self.calls = []

        class _Messages:
            def __init__(inner, outer):
                inner.outer = outer

            def create(inner, **kwargs):
                # Snapshot the messages list — the agent mutates it in place.
                kwargs = {**kwargs, "messages": list(kwargs["messages"])}
                inner.outer.calls.append(kwargs)
                return inner.outer._script.pop(0)

        self.messages = _Messages(self)


def _tool_use(name, input):
    return _Resp([_Block("tool_use", name="use_skill", id="t1", input={"name": name})], "tool_use")


def _final_json(payload):
    return _Resp([_Block("text", text=f"```json\n{payload}\n```")], "end_turn")


def _sofia():
    return Client(id="sofia", name="Sofia", goal="Return to running post-ACL",
                  notes="9 months post knee surgery; cleared for light loading")


def _maya():
    return Client(id="maya", name="Maya", goal="Marathon in 10 weeks")


def test_triage_forces_skill_and_parses_escalation():
    agent = KiwiAgent(
        client=FakeClient([
            _tool_use("flag-health-risk", {}),
            _final_json(
                '{"decision": "escalate", "reason": "new sharp post-surgical knee '
                'pain, movement-provoked", "recommended_action": "Pause loaded leg '
                'work; advise Sofia contact her physio."}'
            ),
        ])
    )
    obs = Observation(client_id="sofia", date=TODAY, source="client_message",
                      text="sharp pain in my surgical knee, worse going downstairs")
    esc = agent.triage(_sofia(), obs)

    assert esc.decision == "escalate"
    assert "physio" in esc.recommended_action
    # First call must force the use_skill tool — triage cannot skip its skill.
    first = agent._client.calls[0]
    assert first["tool_choice"] == {"type": "tool", "name": "use_skill"}
    # The forced skill body was actually fed back as a tool_result.
    second_msgs = agent._client.calls[1]["messages"]
    tool_result = second_msgs[-1]["content"][0]
    assert tool_result["type"] == "tool_result"
    assert "escalate" in tool_result["content"].lower()


def test_escalation_is_recorded_only_for_the_right_client():
    agent = KiwiAgent(
        client=FakeClient([
            _tool_use("flag-health-risk", {}),
            _final_json('{"decision": "escalate", "reason": "x", "recommended_action": "y"}'),
        ])
    )
    obs = Observation(client_id="sofia", date=TODAY, source="client_message", text="knee pain")
    agent.triage(_sofia(), obs)

    # Sofia's memory has the escalation; Maya's is untouched.
    assert "ESCALATE" in agent.memory.context_for("sofia", TODAY)
    assert agent.memory.context_for("maya", TODAY).startswith("(no notes yet")


def test_routine_decision_writes_no_memory():
    agent = KiwiAgent(
        client=FakeClient([
            _tool_use("flag-health-risk", {}),
            _final_json('{"decision": "none", "reason": "textbook DOMS", "recommended_action": ""}'),
        ])
    )
    obs = Observation(client_id="maya", date=TODAY, source="client_message",
                      text="legs wrecked after the long run")
    esc = agent.triage(_maya(), obs)

    assert esc.decision == "none"
    assert agent.memory.context_for("maya", TODAY).startswith("(no notes yet")
