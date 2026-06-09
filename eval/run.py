"""Run the Agent Kiwi evaluation suite. One command, outcome-graded, gated.

    python -m eval.run                  # run everything, print a scoreboard
    python -m eval.run --threshold 0.9  # fail (exit 1) below this pass rate
    python -m eval.run --list           # list cases without calling the model

Design choices that make this an *engineer's* test of a non-deterministic system:
  - Outcome, not path. We assert the escalation tier and the qualitative result,
    never the specific tokens the model emitted or which tools it called.
  - Asymmetric safety cases. Escalation positives AND over-escalation negatives,
    so the gate punishes both missing a real risk and crying wolf.
  - Context isolation is an auto-fail. Isolation cases seed a decoy client and
    fail hard on any leak — these can't be "mostly fine".
  - A machine-readable result (badge.json) feeds a live status badge; the monthly
    GitHub Actions cron keeps it honest over time as the model drifts.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Make the repo root importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwi.agent import KiwiAgent  # noqa: E402
from kiwi.domain import Client, Observation  # noqa: E402
from kiwi.memory import MemoryStore, author_entry  # noqa: E402
from eval import judge  # noqa: E402

CASES_PATH = Path(__file__).parent / "cases.jsonl"
BADGE_PATH = Path(__file__).parent / "badge.json"
RESULTS_PATH = Path(__file__).parent / "last_run.json"
RUN_DATE = "2026-06-07"  # fixed "today" so seeded memory ages deterministically


@dataclass
class CaseResult:
    id: str
    category: str
    passed: bool
    reason: str


def load_cases() -> list[dict]:
    cases = []
    for line in CASES_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            cases.append(json.loads(line))
    return cases


def _seed_store(case: dict) -> MemoryStore:
    """Build a memory store from the case's seed + any decoy clients."""
    store = MemoryStore()
    client_id = case["client"]["id"]
    for entry in case.get("memory_seed", []):
        store.add(client_id, author_entry(today=RUN_DATE, **entry))
    for other_id, entries in case.get("decoys", {}).items():
        for entry in entries:
            store.add(other_id, author_entry(today=RUN_DATE, **entry))
    return store


def _run_case(case: dict, anthropic_client) -> CaseResult:
    client = Client(**case["client"])
    store = _seed_store(case)
    agent = KiwiAgent(memory=store, client=anthropic_client)
    channel = case["channel"]
    grader = case["grader"]

    # Dispatch to the right channel and grade by the case's strategy.
    if grader == "decision":
        obs = Observation(client.id, RUN_DATE, "client_message", case["input"])
        esc = agent.triage(client, obs)
        g = judge.grade_decision(case, esc.decision)

    elif grader == "forbidden":
        text = _produce_text(agent, client, channel, case)
        g = judge.grade_forbidden(case, text)

    elif grader == "rubric":
        text = _produce_text(agent, client, channel, case)
        # The judge sees the memory the agent had — fidelity ("don't invent
        # facts") is unjudgeable without the ground truth to compare against.
        memory_context = store.context_for(client.id, RUN_DATE)
        g = judge.grade_rubric(case, text, anthropic_client, memory_context)

    else:
        g = judge.Grade(False, f"unknown grader {grader!r}")

    return CaseResult(case["id"], case["category"], g.passed, g.reason)


def _produce_text(agent: KiwiAgent, client: Client, channel: str, case: dict) -> str:
    """Run the requested channel and return the text output to grade."""
    if channel == "chat":
        return agent.chat(client, case["input"], RUN_DATE)
    if channel == "summarize":
        return agent.summarize_for_coach(client, RUN_DATE)
    if channel == "daily":
        return agent.daily_run(client, [], RUN_DATE).text
    if channel == "triage":
        obs = Observation(client.id, RUN_DATE, "client_message", case["input"])
        return agent.triage(client, obs).reason
    raise ValueError(f"unknown channel {channel!r}")


def _make_client():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(
            "ANTHROPIC_API_KEY is not set. The eval exercises the live agent and "
            "judge, so it needs a key. (Use --list to inspect cases offline.)"
        )
    import anthropic

    return anthropic.Anthropic()


def _write_badge(passed: int, total: int) -> None:
    rate = passed / total if total else 0.0
    color = "brightgreen" if rate == 1.0 else "yellow" if rate >= 0.9 else "red"
    BADGE_PATH.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "label": "agent eval",
                "message": f"{passed}/{total} passing",
                "color": color,
            }
        ),
        encoding="utf-8",
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the Agent Kiwi eval suite.")
    ap.add_argument("--threshold", type=float, default=1.0,
                    help="minimum pass rate to exit 0 (default 1.0)")
    ap.add_argument("--list", action="store_true", help="list cases and exit")
    ap.add_argument("--limit", type=int, default=0, help="run only the first N cases")
    args = ap.parse_args()

    cases = load_cases()
    if args.limit:
        cases = cases[: args.limit]

    if args.list:
        for c in cases:
            print(f"  [{c['category']:11}] {c['id']:32} via {c['channel']} / {c['grader']}")
        print(f"\n{len(cases)} cases.")
        return 0

    anthropic_client = _make_client()

    results: list[CaseResult] = []
    for c in cases:
        try:
            r = _run_case(c, anthropic_client)
        except Exception as exc:  # a crash on a case is a failure, not a stop
            r = CaseResult(c["id"], c.get("category", "?"), False, f"error: {exc}")
        results.append(r)
        mark = "PASS" if r.passed else "FAIL"
        print(f"  {mark}  [{r.category:11}] {r.id:32} {('' if r.passed else '— ' + r.reason)}")

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    rate = passed / total if total else 0.0

    # Per-category breakdown.
    print("\nBy category:")
    cats = sorted({r.category for r in results})
    for cat in cats:
        sub = [r for r in results if r.category == cat]
        p = sum(1 for r in sub if r.passed)
        print(f"  {cat:13} {p}/{len(sub)}")

    print(f"\nTOTAL: {passed}/{total} ({rate:.0%})")

    _write_badge(passed, total)
    RESULTS_PATH.write_text(
        json.dumps(
            {
                "ran_at": datetime.now(timezone.utc).isoformat(),
                "passed": passed,
                "total": total,
                "rate": rate,
                "results": [r.__dict__ for r in results],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if rate < args.threshold:
        print(f"\nFAILED gate: {rate:.0%} < {args.threshold:.0%}")
        return 1
    print("\nPASSED gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
