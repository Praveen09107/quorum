"""Real tests for gate/anonymization.py (DEC-125)."""
import random

from quorum_backend.gate.anonymization import randomize_objection_order
from quorum_backend.gate.schemas import Objection


def _objections() -> list[Objection]:
    return [
        Objection(category="tone", severity="low", description="first", signed_off=False),
        Objection(category="safety", severity="high", description="second", signed_off=False),
        Objection(category="completeness", severity="medium", description="third", signed_off=False),
        Objection(category="factual", severity="low", description="fourth", signed_off=False),
    ]


def test_randomize_objection_order_never_mutates_the_caller_list():
    original = _objections()
    original_copy = list(original)
    randomize_objection_order(original, rng=random.Random(1))
    assert original == original_copy


def test_randomize_objection_order_preserves_the_real_multiset():
    objections = _objections()
    shuffled = randomize_objection_order(objections, rng=random.Random(42))
    assert sorted(o.description for o in shuffled) == sorted(o.description for o in objections)
    assert len(shuffled) == len(objections)


def test_randomize_objection_order_is_a_real_deterministic_shuffle_given_a_seeded_rng():
    objections = _objections()
    result_1 = randomize_objection_order(objections, rng=random.Random(7))
    result_2 = randomize_objection_order(objections, rng=random.Random(7))
    assert [o.description for o in result_1] == [o.description for o in result_2]


def test_randomize_objection_order_actually_changes_order_for_a_real_multi_item_list():
    # Not a statistical flake -- a fixed seed known to produce a real,
    # non-identity permutation of this exact 4-item list.
    objections = _objections()
    shuffled = randomize_objection_order(objections, rng=random.Random(3))
    assert [o.description for o in shuffled] != [o.description for o in objections]


def test_randomize_objection_order_handles_zero_and_one_item_lists_honestly():
    assert randomize_objection_order([]) == []
    single = [Objection(category="tone", severity="low", description="only", signed_off=True)]
    assert randomize_objection_order(single) == single
