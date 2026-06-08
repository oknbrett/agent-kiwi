"""client_memory v2.1 — structured decision journal (pure, testable core).

A Python port of the production memory engine I built for a private multi-tenant
agent, adapted to the coaching domain. It is deliberately framework-free so the
deterministic logic can be unit-tested without any LLM or network.

Design (one journal per client; the client is the isolation root):
  confidence    — observations carry a weight in [0,1]; they decay out instead of
                  living forever. Below CONFIDENCE_FLOOR they stop surfacing.
  subtype       — observations are training | recovery | adherence.
  trigger       — observations carry an explicit fire condition.
  derived_from  — provenance pointers to the entries an observation was distilled
                  from. When all sources are gone, confidence drops (cascade).
  importance    — per-entry signal weight; reflection fires on accumulated
                  importance, not on entry count.
  last_reflected_at — marks the boundary of already-reflected entries.

Isolation invariant: every public read/write is scoped by client_id. One
client's memory can never appear in another client's context. `MemoryStore`
enforces this and `tests/test_memory_isolation.py` proves it.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta
from typing import Literal, Optional

MemoryEntryType = Literal[
    "escalation_decision",  # Kiwi flagged something to the coach
    "checkin_sent",  # Kiwi sent a client a check-in
    "waiting_for_reply",  # client hasn't responded yet
    "client_profile",  # static facts (goal, injury history) — never decay
    "observation",  # a learned pattern about the client
]

ObservationSubtype = Literal["training", "recovery", "adherence"]

# ── Tunables (identical to the production v2.1 engine) ─────────────────────────
CONFIDENCE_FLOOR = 0.3  # below this, an observation stops surfacing
DEFAULT_CONFIDENCE = 1.0
CONFIRM_STEP = 0.1  # reinforcement raises confidence
CONTRADICT_STEP = 0.2  # contradiction lowers it ~2x (asymmetric, hindsight rule)
PRUNE_AFTER_DAYS = 60  # episodic entries age out after this
ENTRY_HARD_CAP = 80
REFLECTION_IMPORTANCE_THRESHOLD = 20  # reflection trigger

# Default per-type importance. Escalations are the most reflection-worthy.
_IMPORTANCE_BY_TYPE: dict[str, int] = {
    "escalation_decision": 8,
    "observation": 5,
    "waiting_for_reply": 4,
    "client_profile": 3,
    "checkin_sent": 2,
}


def default_importance(entry_type: MemoryEntryType) -> int:
    return _IMPORTANCE_BY_TYPE.get(entry_type, 3)


@dataclass
class MemoryEntry:
    body: str
    type: MemoryEntryType = "observation"
    at: str = ""  # YYYY-MM-DD, filled by author_entry
    id: str = ""
    expires: Optional[str] = None  # YYYY-MM-DD — ignored after this date
    subject: Optional[str] = None  # who/what this is about
    item: Optional[str] = None  # human-readable label
    # v2.1 fields
    subtype: Optional[ObservationSubtype] = None  # observations only
    trigger: Optional[str] = None  # observations only — explicit fire condition
    confidence: Optional[float] = None  # observations only — [0,1]
    importance: Optional[int] = None  # 0–10
    derived_from: list[str] = field(default_factory=list)  # source entry ids

    def to_dict(self) -> dict:
        d = asdict(self)
        # Keep the JSON tidy: drop empties.
        return {k: v for k, v in d.items() if v not in (None, [], "")}


@dataclass
class MemoryDoc:
    version: int = 2
    entries: list[MemoryEntry] = field(default_factory=list)
    last_reflected_at: Optional[str] = None

    def to_dict(self) -> dict:
        out: dict = {"version": self.version, "entries": [e.to_dict() for e in self.entries]}
        if self.last_reflected_at:
            out["last_reflected_at"] = self.last_reflected_at
        return out


def empty_memory_doc() -> MemoryDoc:
    return MemoryDoc(version=2, entries=[])


def _gen_id() -> str:
    return uuid.uuid4().hex[:12]


def author_entry(
    *,
    body: str,
    type: MemoryEntryType = "observation",
    today: str,
    expires: Optional[str] = None,
    subject: Optional[str] = None,
    item: Optional[str] = None,
    subtype: Optional[ObservationSubtype] = None,
    trigger: Optional[str] = None,
    confidence: Optional[float] = None,
    importance: Optional[int] = None,
    derived_from: Optional[list[str]] = None,
    id: Optional[str] = None,
    at: Optional[str] = None,
) -> MemoryEntry:
    """Build a complete entry from partial input, filling v2.1 defaults."""
    entry = MemoryEntry(
        body=body,
        type=type,
        at=at or today,
        id=id or _gen_id(),
        importance=importance if importance is not None else default_importance(type),
        expires=expires,
        subject=subject,
        item=item,
        derived_from=list(derived_from) if derived_from else [],
    )
    if type == "observation":
        entry.confidence = confidence if confidence is not None else DEFAULT_CONFIDENCE
        entry.subtype = subtype
        entry.trigger = trigger
    return entry


def validate_entry(entry: MemoryEntry) -> Optional[str]:
    """Observations must carry an explicit trigger. Returns error string or None."""
    if entry.type == "observation":
        if not entry.trigger or not entry.trigger.strip():
            return (
                "observation requires a 'trigger' — the explicit condition under "
                "which this pattern applies (e.g. \"client silent 48h after a "
                "missed session\"). A restatement of the body is not a trigger."
            )
    return None


def next_confidence(current: Optional[float], kind: Literal["confirm", "contradict"]) -> float:
    """Confidence update on new evidence. Contradiction moves ~2x a confirm."""
    base = DEFAULT_CONFIDENCE if current is None else current
    if kind == "confirm":
        return min(1.0, round(base + CONFIRM_STEP, 4))
    return max(0.0, round(base - CONTRADICT_STEP, 4))


def _days_ago(today: str, n: int) -> str:
    d = date.fromisoformat(today) - timedelta(days=n)
    return d.isoformat()


def compact_entries(entries: list[MemoryEntry], today: str) -> list[MemoryEntry]:
    """Deterministic compaction — no AI call needed because entries are structured.

    Applied in order:
      1. Drop entries past their explicit `expires` date.
      2. Provenance cascade: an observation whose source entries are all gone can
         no longer be re-confirmed — push its confidence below the floor.
      3. Prune:
           client_profile -> always kept (semantic facts, never decay).
           observation    -> kept iff confidence >= CONFIDENCE_FLOOR.
           episodic       -> kept iff newer than PRUNE_AFTER_DAYS.
      4. Hard cap at ENTRY_HARD_CAP: trim oldest, protecting client_profile.
    """
    live = [e for e in entries if not e.expires or e.expires >= today]

    live_ids = {e.id for e in live}
    for e in live:
        if e.type == "observation" and e.derived_from:
            any_source_left = any(src in live_ids for src in e.derived_from)
            if not any_source_left:
                cur = DEFAULT_CONFIDENCE if e.confidence is None else e.confidence
                e.confidence = min(cur, CONFIDENCE_FLOOR - 0.05)

    cutoff = _days_ago(today, PRUNE_AFTER_DAYS)

    def keep(e: MemoryEntry) -> bool:
        if e.type == "client_profile":
            return True
        if e.type == "observation":
            return (DEFAULT_CONFIDENCE if e.confidence is None else e.confidence) >= CONFIDENCE_FLOOR
        return e.at >= cutoff

    pruned = [e for e in live if keep(e)]
    if len(pruned) <= ENTRY_HARD_CAP:
        return pruned

    ordered = sorted(pruned, key=lambda e: e.at)
    profile = [e for e in ordered if e.type == "client_profile"]
    rest = [e for e in ordered if e.type != "client_profile"]
    keep_n = ENTRY_HARD_CAP - len(profile)
    return profile + rest[-keep_n:]


def visible_entries(doc: MemoryDoc, today: str) -> list[MemoryEntry]:
    """Entries that should currently surface: not expired, not a faded observation."""
    out = []
    for e in doc.entries:
        if e.expires and e.expires < today:
            continue
        if e.type == "observation" and (
            (DEFAULT_CONFIDENCE if e.confidence is None else e.confidence) < CONFIDENCE_FLOOR
        ):
            continue
        out.append(e)
    return out


_TYPE_LABELS: dict[str, str] = {
    "escalation_decision": "ESCALATION DECISIONS",
    "waiting_for_reply": "WAITING FOR REPLY",
    "checkin_sent": "CHECK-INS SENT",
    "client_profile": "CLIENT PROFILE",
    "observation": "OBSERVATIONS",
}
_TYPE_ORDER: list[MemoryEntryType] = [
    "escalation_decision",
    "waiting_for_reply",
    "checkin_sent",
    "client_profile",
    "observation",
]


def format_memory_for_claude(doc: MemoryDoc, today: str) -> str:
    """Render the visible memory into the context block injected at prompt time."""
    active = visible_entries(doc, today)
    if not active:
        return "(no notes yet — this is your first run with this client)"

    by_type: dict[str, list[MemoryEntry]] = {}
    for e in active:
        by_type.setdefault(e.type, []).append(e)

    lines: list[str] = [f"Memory ({len(active)} entries):\n"]
    for t in _TYPE_ORDER:
        group = by_type.get(t)
        if not group:
            continue
        lines.append(f"{_TYPE_LABELS.get(t, t.upper())}:")
        for e in sorted(group, key=lambda x: x.at, reverse=True):
            parts = [e.at]
            if e.item:
                parts.append(e.item)
            if e.subject:
                parts.append(e.subject)
            lines.append(f"  [{' | '.join(parts)}] {e.body}")
            if e.type == "observation":
                if e.subtype and e.trigger:
                    lines.append(f"    {e.subtype} — when: {e.trigger}")
                elif e.trigger:
                    lines.append(f"    when: {e.trigger}")
                conf = DEFAULT_CONFIDENCE if e.confidence is None else e.confidence
                if conf < 0.7:
                    lines.append(f"    confidence: {conf:.2f}")
            if e.expires:
                lines.append(f"    -> ignore after {e.expires}")
        lines.append("")
    return "\n".join(lines).strip()


def cumulative_importance_since(doc: MemoryDoc) -> int:
    """Sum the importance of entries authored after the last reflection boundary."""
    since = doc.last_reflected_at or ""
    total = 0
    for e in doc.entries:
        if since and e.at <= since:
            continue
        if e.type == "client_profile":  # static facts aren't reflection signal
            continue
        total += e.importance if e.importance is not None else default_importance(e.type)
    return total


def should_reflect(doc: MemoryDoc, threshold: int = REFLECTION_IMPORTANCE_THRESHOLD) -> bool:
    return cumulative_importance_since(doc) > threshold


# ── Per-client store — the isolation boundary ─────────────────────────────────


class MemoryStore:
    """Holds one MemoryDoc per client and enforces the isolation invariant.

    There is no API to read across clients. Every method takes a client_id and
    touches only that client's journal. This mirrors row-level security in the
    production system: the caller can only ever see its own tenant's rows.
    """

    def __init__(self) -> None:
        self._docs: dict[str, MemoryDoc] = {}

    def doc(self, client_id: str) -> MemoryDoc:
        return self._docs.setdefault(client_id, empty_memory_doc())

    def add(self, client_id: str, entry: MemoryEntry) -> None:
        err = validate_entry(entry)
        if err:
            raise ValueError(err)
        self.doc(client_id).entries.append(entry)

    def context_for(self, client_id: str, today: str) -> str:
        """The ONLY way to get memory into a prompt — always single-client scoped."""
        return format_memory_for_claude(self.doc(client_id), today)

    def compact(self, client_id: str, today: str) -> None:
        d = self.doc(client_id)
        d.entries = compact_entries(d.entries, today)

    def client_ids(self) -> list[str]:
        return list(self._docs.keys())

    # Persistence (round-trips through plain JSON so a run is reproducible).
    def to_json(self) -> str:
        return json.dumps({cid: d.to_dict() for cid, d in self._docs.items()}, indent=2)
