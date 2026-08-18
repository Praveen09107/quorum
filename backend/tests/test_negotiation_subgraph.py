"""Real tests for negotiation/subgraph.py -- the capstone proving four
sessions built at genuinely different points in the project timeline
(IMPL_18-20) compose correctly as one real, running pipeline."""
from quorum_backend.gate.schemas import NegotiationOption, Position, ResourceClaim
from quorum_backend.negotiation.impact_simulator import DomainSnapshot, OptionEffect
from quorum_backend.negotiation.subgraph import NegotiationState, build_negotiation_graph
from quorum_backend.negotiation.trigger import DomainState


async def test_non_conflict_short_circuits_before_any_llm_call():
    # A stronger, more honest proof than checking output alone: tracks
    # whether position_call or synthesis_call were ever invoked at all. A
    # bug that accidentally called both and then discarded the results
    # would still produce a correct-looking final state -- this test
    # would catch that; a state-only assertion wouldn't.
    position_calls_seen: list[str] = []
    synthesis_calls_seen: list[str] = []

    async def tracking_position_call(domain: str) -> Position:
        position_calls_seen.append(domain)
        return Position(domain=domain, concern="x", severity_claim="x", resource_claims=[], proposed_resolution="x")

    async def tracking_synthesis_call(prompt: str) -> list[NegotiationOption]:
        synthesis_calls_seen.append(prompt)
        return []

    def fake_effect_extractor(option: NegotiationOption) -> OptionEffect:
        return OptionEffect()

    graph = build_negotiation_graph(tracking_position_call, tracking_synthesis_call, fake_effect_extractor)

    state: NegotiationState = {
        "resource_claims": [ResourceClaim(claim_type="money", amount=100, unit="currency_minor_units")],
        "domain_states": {"finance": DomainState(domain="finance", available=1000, unit="currency_minor_units")},
        "baseline": DomainSnapshot(deadline_slack_hours=5.0, budget_remaining_fraction=0.5, task_hours_committed=10.0),
        "conflicted_domains": None,
        "triggers_negotiation": None,
        "positions": None,
        "options": None,
        "impact": None,
    }

    result = await graph.ainvoke(state)

    assert position_calls_seen == []
    assert synthesis_calls_seen == []
    assert result["triggers_negotiation"] is False
    assert result["positions"] is None
    assert result["options"] is None
    assert result["impact"] is None


async def test_full_negotiation_pipeline_runs_end_to_end_on_a_real_conflict():
    # The first test in this project to run the trigger, position
    # generation, synthesis, and impact simulation in one real, continuous
    # sequence.
    async def fake_position_call(domain: str) -> Position:
        return Position(
            domain=domain,
            concern=f"{domain} is over-committed",
            severity_claim="high",
            resource_claims=[],
            proposed_resolution=f"free up {domain} capacity",
        )

    async def fake_synthesis_call(prompt: str) -> list[NegotiationOption]:
        assert "free up finance capacity" in prompt or "free up tasks capacity" in prompt
        return [
            NegotiationOption(option_id="option_a", description="reduce spend", source_domains=["finance"]),
            NegotiationOption(option_id="option_b", description="drop a task", source_domains=["tasks"]),
            NegotiationOption(option_id="do_nothing", description="do nothing"),
        ]

    def fake_effect_extractor(option: NegotiationOption) -> OptionEffect:
        if option.option_id == "option_a":
            return OptionEffect(budget_remaining_fraction_change=0.1)
        if option.option_id == "option_b":
            return OptionEffect(task_hours_committed_change=-2.0)
        return OptionEffect()

    graph = build_negotiation_graph(fake_position_call, fake_synthesis_call, fake_effect_extractor)

    state: NegotiationState = {
        "resource_claims": [
            ResourceClaim(claim_type="money", amount=500, unit="currency_minor_units"),
            ResourceClaim(claim_type="effort", amount=20, unit="hours"),
        ],
        "domain_states": {
            "finance": DomainState(domain="finance", available=200, unit="currency_minor_units"),
            "tasks": DomainState(domain="tasks", available=5, unit="hours"),
        },
        "baseline": DomainSnapshot(deadline_slack_hours=5.0, budget_remaining_fraction=0.5, task_hours_committed=10.0),
        "conflicted_domains": None,
        "triggers_negotiation": None,
        "positions": None,
        "options": None,
        "impact": None,
    }

    result = await graph.ainvoke(state)

    assert result["triggers_negotiation"] is True
    assert sorted(state_domain.domain for state_domain in result["positions"]) == ["finance", "tasks"]
    assert len(result["options"]) == 3
    assert set(result["impact"].keys()) == {"option_a", "option_b", "do_nothing"}

    by_metric = {d.metric: d for d in result["impact"]["option_a"]}
    assert by_metric["budget_remaining_fraction"].direction == "improves"

    by_metric = {d.metric: d for d in result["impact"]["option_b"]}
    assert by_metric["task_hours_committed"].direction == "improves"

    assert all(d.direction == "unchanged" for d in result["impact"]["do_nothing"])
