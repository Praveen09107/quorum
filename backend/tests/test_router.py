"""Real tests for router.py -- stakes lookup + complexity classification."""
import pytest

from quorum_backend.gate.schemas import ActionType
from quorum_backend.router import (
    STAKES_TABLE,
    Complexity,
    ComplexitySignals,
    compute_complexity,
    get_stakes,
)


def test_stakes_table_covers_all_real_action_types():
    missing = set(ActionType) - set(STAKES_TABLE.keys())
    assert not missing, f"Missing stakes-table entries: {missing}"


def test_get_stakes_raises_on_unmapped_type():
    # A real ActionType always resolves; an unmapped/invalid value must
    # raise loudly, never silently default.
    with pytest.raises(ValueError):
        get_stakes("not_a_real_action_type")  # type: ignore[arg-type]


def test_get_stakes_returns_real_mapped_values():
    assert get_stakes(ActionType.LABEL_EMAIL) == STAKES_TABLE[ActionType.LABEL_EMAIL]
    assert get_stakes(ActionType.SEND_EMAIL) == STAKES_TABLE[ActionType.SEND_EMAIL]


def test_multi_domain_is_always_c2_regardless_of_other_signals():
    signals = ComplexitySignals(
        domain_count=2, requires_cross_reference=False, is_ambiguous=False, text_length=10
    )
    assert compute_complexity(signals) == Complexity.C2


def test_ambiguous_single_domain_is_c1():
    signals = ComplexitySignals(
        domain_count=1, requires_cross_reference=False, is_ambiguous=True, text_length=10
    )
    assert compute_complexity(signals) == Complexity.C1


def test_long_unstructured_text_falls_back_to_c1_conservatively():
    signals = ComplexitySignals(
        domain_count=1, requires_cross_reference=False, is_ambiguous=False, text_length=281
    )
    assert compute_complexity(signals) == Complexity.C1


def test_short_simple_single_domain_is_c0():
    signals = ComplexitySignals(
        domain_count=1, requires_cross_reference=False, is_ambiguous=False, text_length=50
    )
    assert compute_complexity(signals) == Complexity.C0


def test_expense_logging_is_c0_not_raised_by_financial_content_alone():
    # "spent 450 on groceries at DMart" -- Sprint 0's own real on-device
    # test prompt. Recording a new fact needs no cross-reference against
    # existing state -- financial content alone must never raise complexity.
    signals = ComplexitySignals(
        domain_count=1, requires_cross_reference=False, is_ambiguous=False, text_length=32
    )
    assert compute_complexity(signals) == Complexity.C0


def test_meeting_move_request_is_c1_because_it_needs_calendar_lookup():
    # "Can we move our 3pm to Thursday instead?" -- correctness genuinely
    # depends on checking the real calendar, the actual distinguishing
    # signal, not the mere presence of a time reference.
    signals = ComplexitySignals(
        domain_count=1, requires_cross_reference=True, is_ambiguous=False, text_length=41
    )
    assert compute_complexity(signals) == Complexity.C1
