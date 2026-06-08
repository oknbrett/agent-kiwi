"""The isolation invariant: one client's memory never appears in another's context.

This is the public analogue of the two-tenant RLS isolation test from the
production system. It is the single most important guarantee in the memory layer
and an automatic-fail case in the eval suite.
"""

from kiwi.memory import MemoryStore, author_entry

TODAY = "2026-06-07"


def _store_with_two_clients() -> MemoryStore:
    store = MemoryStore()
    store.add(
        "maya",
        author_entry(
            body="Targeting a sub-4:00 marathon; responds well to volume.",
            type="client_profile",
            today=TODAY,
        ),
    )
    store.add(
        "sofia",
        author_entry(
            body="Post-ACL-reconstruction, 8 weeks; load surgical knee conservatively.",
            type="client_profile",
            today=TODAY,
        ),
    )
    return store


def test_context_is_single_client_scoped():
    store = _store_with_two_clients()

    maya_ctx = store.context_for("maya", TODAY)
    sofia_ctx = store.context_for("sofia", TODAY)

    # Maya's context must contain only Maya's facts.
    assert "marathon" in maya_ctx
    assert "ACL" not in maya_ctx
    assert "surgical knee" not in maya_ctx

    # Sofia's context must contain only Sofia's facts.
    assert "ACL" in sofia_ctx
    assert "marathon" not in sofia_ctx


def test_no_cross_client_leak_after_many_writes():
    store = _store_with_two_clients()
    # Hammer Maya's journal with many observations.
    for i in range(25):
        store.add(
            "maya",
            author_entry(
                body=f"Long-run note #{i}",
                type="observation",
                trigger="weekly long run logged",
                today=TODAY,
            ),
        )
    sofia_ctx = store.context_for("sofia", TODAY)
    assert "Long-run note" not in sofia_ctx
    # And a brand-new client sees nothing at all.
    assert store.context_for("nobody", TODAY).startswith("(no notes yet")


def test_unknown_client_is_empty_not_error():
    store = MemoryStore()
    ctx = store.context_for("ghost", TODAY)
    assert "no notes yet" in ctx
    assert store.client_ids() == ["ghost"]  # created lazily, still isolated
