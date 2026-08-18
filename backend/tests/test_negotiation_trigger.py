"""Real tests for negotiation/trigger.py."""
from quorum_backend.gate.schemas import ResourceClaim
from quorum_backend.negotiation.trigger import DomainState, scan_for_conflicts


def test_single_domain_conflict_does_not_trigger_negotiation():
    claims = [ResourceClaim(claim_type="money", amount=500, unit="currency_minor_units")]
    states = {"finance": DomainState("finance", available=200, unit="currency_minor_units")}
    result = scan_for_conflicts(claims, states)
    assert result.triggers_negotiation is False


def test_two_domain_conflict_triggers_negotiation():
    # The real, named scenario: interview-vs-deadline-vs-fee -- here a
    # genuine two-domain collision (time + money both over real capacity).
    claims = [
        ResourceClaim(claim_type="time", amount=3.0, unit="hours"),
        ResourceClaim(claim_type="money", amount=500.0, unit="currency_minor_units"),
    ]
    states = {
        "calendar": DomainState("calendar", available=1.0, unit="hours"),
        "finance": DomainState("finance", available=200.0, unit="currency_minor_units"),
    }
    result = scan_for_conflicts(claims, states)
    assert result.triggers_negotiation is True
    assert set(result.conflicted_domains) == {"calendar", "finance"}


def test_claim_with_no_matching_domain_state_is_never_treated_as_a_conflict():
    claims = [ResourceClaim(claim_type="money", amount=500, unit="x")]
    result = scan_for_conflicts(claims, {})
    assert result.conflicted_domains == []
    assert result.triggers_negotiation is False


def test_claim_within_available_capacity_is_not_a_conflict():
    claims = [ResourceClaim(claim_type="effort", amount=2.0, unit="hours")]
    states = {"tasks": DomainState("tasks", available=5.0, unit="hours")}
    result = scan_for_conflicts(claims, states)
    assert result.conflicted_domains == []


def test_three_domain_conflict_also_triggers():
    claims = [
        ResourceClaim(claim_type="time", amount=3.0, unit="hours"),
        ResourceClaim(claim_type="money", amount=500.0, unit="x"),
        ResourceClaim(claim_type="effort", amount=10.0, unit="hours"),
    ]
    states = {
        "calendar": DomainState("calendar", available=1.0, unit="hours"),
        "finance": DomainState("finance", available=200.0, unit="x"),
        "tasks": DomainState("tasks", available=2.0, unit="hours"),
    }
    result = scan_for_conflicts(claims, states)
    assert result.triggers_negotiation is True
    assert set(result.conflicted_domains) == {"calendar", "finance", "tasks"}


def test_deterministic_same_inputs_produce_same_output():
    claims = [
        ResourceClaim(claim_type="time", amount=3.0, unit="hours"),
        ResourceClaim(claim_type="money", amount=500.0, unit="x"),
    ]
    states = {
        "calendar": DomainState("calendar", available=1.0, unit="hours"),
        "finance": DomainState("finance", available=200.0, unit="x"),
    }
    results = [scan_for_conflicts(claims, states) for _ in range(20)]
    assert all(r == results[0] for r in results)
