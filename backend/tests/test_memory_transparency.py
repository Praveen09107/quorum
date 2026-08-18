"""Real tests for security/memory_transparency.py."""
from datetime import datetime, timezone

from quorum_backend.security.memory_transparency import Memory, group_by_category


def _memory(memory_id: str, category: str) -> Memory:
    return Memory(memory_id=memory_id, content="x", category=category, created_at=datetime.now(timezone.utc))


def test_group_by_category_groups_memories_correctly():
    memories = [
        _memory("1", "preference"),
        _memory("2", "preference"),
        _memory("3", "fact"),
    ]
    grouped = group_by_category(memories)
    assert [m.memory_id for m in grouped["preference"]] == ["1", "2"]
    assert [m.memory_id for m in grouped["fact"]] == ["3"]


def test_group_by_category_never_drops_a_memory_for_an_unrecognized_category():
    memories = [_memory("1", "preference"), _memory("2", "a_genuinely_new_category")]
    grouped = group_by_category(memories)
    assert "a_genuinely_new_category" in grouped
    assert len(grouped["a_genuinely_new_category"]) == 1


def test_group_by_category_accounts_for_every_real_memory_across_all_groups():
    memories = [_memory("1", "preference"), _memory("2", "a_genuinely_new_category")]
    grouped = group_by_category(memories)
    total_grouped = sum(len(v) for v in grouped.values())
    assert total_grouped == len(memories)


def test_group_by_category_returns_an_empty_dict_for_no_memories():
    assert group_by_category([]) == {}
