"""Replay a scripted week through the real agent — the end-to-end demo.

    python simulate_week.py

Reads data/clients.json (four clients, Monday→Friday observations) and runs each
day through the agent and the coach channel, printing the recommendation-first
coach digest for that day. The week is written to build to Friday, when Sofia
reports sharp post-surgical knee pain and Kiwi escalates it to the human coach
while correctly leaving Maya's marathon DOMS alone.

Needs ANTHROPIC_API_KEY (it drives the live agent). This is the thing to record
as a terminal GIF for the README.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from kiwi.agent import KiwiAgent
from kiwi.coach import build_digest, render_digest
from kiwi.domain import Client, Observation
from kiwi.memory import MemoryStore, author_entry
from kiwi.resilience import configure_logging

DATA = Path(__file__).parent / "data" / "clients.json"


def _load() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def _seed(store: MemoryStore, seed_memory: dict) -> None:
    for client_id, entries in seed_memory.items():
        for entry in entries:
            at = entry.get("at")
            store.add(client_id, author_entry(today=at or "2026-05-01", **entry))


def main() -> int:
    # `--trace` turns on the JSON-lines call trace (every model attempt, its
    # latency, retries, and token usage) so the resilience layer is visible.
    if "--trace" in sys.argv:
        configure_logging()

    cfg = _load()
    clients = [Client(**c) for c in cfg["clients"]]
    by_id = {c.id: c for c in clients}

    store = MemoryStore()
    _seed(store, cfg.get("seed_memory", {}))
    agent = KiwiAgent(memory=store)  # real Anthropic client (needs API key)

    for day in sorted(cfg["week"].keys()):
        day_obs = cfg["week"][day]
        observations = {
            cid: [Observation(cid, day, "client_message", text) for text in texts]
            for cid, texts in day_obs.items()
        }
        # Only the clients active that day need triaging; summarise all of them.
        digest = build_digest(agent, clients, observations, day)
        print("\n" + render_digest(digest) + "\n")

    return 0


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        raise SystemExit(0)
    raise SystemExit(main())
