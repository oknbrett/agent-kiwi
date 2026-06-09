"""Confidence dynamics + deterministic compaction.

Locks the v2.1 rules: asymmetric confirm/contradict, the confidence floor,
expiry, the provenance cascade, and the hard cap.
"""

from kiwi.memory import (
    CONFIDENCE_FLOOR,
    CONTRADICT_STEP,
    DEFAULT_CONFIDENCE,
    ENTRY_HARD_CAP,
    MemoryDoc,
    MemoryStore,
    author_entry,
    compact_entries,
    next_confidence,
    should_reflect,
    visible_entries,
)

TODAY = "2026-06-07"


def test_confirm_and_contradict_are_asymmetric():
    # A contradiction must move confidence ~2x as far as a confirmation.
    assert next_confidence(0.5, "confirm") == 0.6
    assert next_confidence(0.5, "contradict") == 0.3
    # Clamped to [0, 1].
    assert next_confidence(1.0, "confirm") == 1.0
    assert next_confidence(0.1, "contradict") == 0.0
    # Default base when no prior confidence.
    assert next_confidence(None, "contradict") == round(DEFAULT_CONFIDENCE - CONTRADICT_STEP, 4)


def test_faded_observation_stops_surfacing():
    doc = MemoryDoc()
    low = author_entry(
        body="Prefers morning sessions",
        type="observation",
        trigger="scheduling a session",
        confidence=CONFIDENCE_FLOOR - 0.01,
        today=TODAY,
    )
    high = author_entry(
        body="Skips sessions when travelling for work",
        type="observation",
        trigger="client mentions travel",
        confidence=0.9,
        today=TODAY,
    )
    doc.entries.extend([low, high])
    visible = visible_entries(doc, TODAY)
    assert high in visible
    assert low not in visible  # below the floor — hidden, not deleted


def test_expired_entry_is_compacted_out():
    doc_entries = [
        author_entry(body="Out of town until the 5th", type="waiting_for_reply",
                     expires="2026-06-05", today="2026-06-01"),
        author_entry(body="Goal: first 10k", type="client_profile", today="2026-06-01"),
    ]
    kept = compact_entries(doc_entries, TODAY)
    bodies = [e.body for e in kept]
    assert "Goal: first 10k" in bodies  # profile never decays
    assert "Out of town until the 5th" not in bodies  # expired


def test_provenance_cascade_fades_orphan_observation():
    parent = author_entry(body="missed Tuesday", type="checkin_sent", today="2026-04-01")
    # Derived observation whose only source will be pruned as stale episodic.
    child = author_entry(
        body="tends to miss mid-week sessions",
        type="observation",
        trigger="a weekday session is scheduled",
        derived_from=[parent.id],
        confidence=0.9,
        today="2026-04-01",
    )
    # Pass 1 (a cron run): parent is >60 days old and ages out; the cascade runs
    # against the still-live set, so the child survives this pass intact.
    pass1 = compact_entries([parent, child], TODAY)
    assert any(e.type == "observation" for e in pass1)
    assert all(e.type != "checkin_sent" for e in pass1)  # parent gone

    # Pass 2 (next cron run): the child's only source is now missing, so the
    # cascade pushes its confidence below the floor and it is pruned. This
    # mirrors the idempotent, multi-run reflection cycle in production.
    pass2 = compact_entries(pass1, TODAY)
    assert all(e.type != "observation" for e in pass2)


def test_hard_cap_protects_profile_and_trims_oldest():
    profile = author_entry(body="Goal: powerlifting meet", type="client_profile", today="2020-01-01")
    entries = [profile]
    for i in range(ENTRY_HARD_CAP + 20):
        # Recent episodic entries so they survive the 60-day prune.
        entries.append(
            author_entry(body=f"checkin {i}", type="checkin_sent",
                         at=TODAY, today=TODAY)
        )
    kept = compact_entries(entries, TODAY)
    assert len(kept) <= ENTRY_HARD_CAP
    assert profile in kept  # the oldest entry, but protected


def test_apply_evidence_moves_only_real_observations():
    store = MemoryStore()
    obs = author_entry(
        body="Skips sessions when work is busy",
        type="observation",
        trigger="a deadline week",
        confidence=0.5,
        today=TODAY,
    )
    profile = author_entry(body="Goal: lose 8kg", type="client_profile", today=TODAY)
    store.add("tom", obs)
    store.add("tom", profile)

    n_confirm, n_contradict = store.apply_evidence(
        "tom",
        confirmed=[obs.id],
        # A hallucinated id and the (confidence-less) profile id must be ignored.
        contradicted=["not-a-real-id", profile.id],
    )
    assert (n_confirm, n_contradict) == (1, 0)
    assert obs.confidence == 0.6
    assert profile.confidence is None  # untouched — profiles carry no confidence


def test_apply_evidence_contradiction_pulls_2x():
    store = MemoryStore()
    obs = author_entry(
        body="Prefers evening sessions",
        type="observation",
        trigger="scheduling a session",
        confidence=0.5,
        today=TODAY,
    )
    store.add("maya", obs)
    store.apply_evidence("maya", confirmed=[], contradicted=[obs.id])
    assert obs.confidence == 0.3  # 0.5 - CONTRADICT_STEP


def test_json_round_trip_is_lossless():
    store = MemoryStore()
    store.add(
        "sofia",
        author_entry(
            body="Post-ACL; light loading only",
            type="client_profile",
            today=TODAY,
        ),
    )
    store.add(
        "sofia",
        author_entry(
            body="Stair-loading aggravates the knee",
            type="observation",
            subtype="recovery",
            trigger="client reports stair use",
            confidence=0.82,
            today=TODAY,
        ),
    )
    store.add("liam", author_entry(body="No reply x2", type="waiting_for_reply", today=TODAY))

    restored = MemoryStore.from_json(store.to_json())
    assert restored.to_json() == store.to_json()
    assert sorted(restored.client_ids()) == ["liam", "sofia"]
    # And the restored store renders identical prompt context.
    assert restored.context_for("sofia", TODAY) == store.context_for("sofia", TODAY)


def test_reflection_triggers_on_accumulated_importance():
    doc = MemoryDoc()
    # 3 escalation_decisions (importance 8 each) = 24 > threshold of 20.
    for i in range(3):
        doc.entries.append(
            author_entry(body=f"escalated knee pain {i}", type="escalation_decision", today=TODAY)
        )
    assert should_reflect(doc) is True

    fresh = MemoryDoc()
    fresh.entries.append(author_entry(body="one check-in", type="checkin_sent", today=TODAY))
    assert should_reflect(fresh) is False
