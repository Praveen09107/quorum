"""Real tests for features/self_test_harness.py -- the real Gate wired
in directly, no stub layer, confirmed by every test here actually
exercising gate.review()."""
from quorum_backend.features.self_test_harness import (
    AdversarialScenario,
    run_self_test,
    summarize,
)
from quorum_backend.gate.schemas import ActionProposal, ActionType, ContextSnapshot, Finding, GateVerdict, Stakes


async def test_run_self_test_against_the_real_default_scenarios_returns_three_real_results():
    results = await run_self_test()
    assert len(results) == 3
    assert {r.scenario_id for r in results} == {
        "S0_clean_approval",
        "S2_stage_a_hard_fail",
        "S3_real_critic_objection_escalates",
    }


async def test_the_s0_clean_approval_scenario_genuinely_approves_via_the_real_gate():
    results = await run_self_test()
    result = next(r for r in results if r.scenario_id == "S0_clean_approval")
    assert result.actual == "approve"
    assert result.passed is True


async def test_the_stage_a_hard_fail_scenario_genuinely_forces_a_revise():
    results = await run_self_test()
    result = next(r for r in results if r.scenario_id == "S2_stage_a_hard_fail")
    assert result.actual == "revise"
    assert result.passed is True


async def test_the_s3_critic_objection_scenario_genuinely_escalates():
    results = await run_self_test()
    result = next(r for r in results if r.scenario_id == "S3_real_critic_objection_escalates")
    assert result.actual == "escalate_to_human"
    assert result.passed is True


async def test_target_other_than_real_gate_fails_loud_never_silently_ignored():
    try:
        await run_self_test(target="stub")
        assert False, "should have raised -- no stub Gate exists in this repository"
    except ValueError as e:
        assert "real_gate" in str(e)


async def test_a_deliberately_mis_specified_scenario_is_reported_as_a_genuine_miss_not_hidden():
    # THE real property this module exists to guarantee (ADD section 9.6):
    # a scenario whose real Gate outcome disagrees with what was expected
    # must be surfaced, never silently swallowed into a false "pass".
    async def judge_approve(proposal, findings, objections):
        return GateVerdict(decision="approve", findings=findings, objections=objections, trace_id=str(proposal.proposal_id))

    clean = lambda proposal: Finding(validator="budget_check", claim="ok", evidence_state="verified_true", confidence=0.9)  # noqa: E731

    deliberately_wrong_scenario = AdversarialScenario(
        scenario_id="deliberately_wrong",
        description="Real Gate will approve this -- expectation is deliberately set to reject to prove misses surface.",
        proposal=ActionProposal(action_type=ActionType.CREATE_NOTE, payload={}, context_used=ContextSnapshot()),
        stakes=Stakes.S0,
        stage_a_checks=[clean],
        critic_call=lambda p, f: [],  # noqa: E731 -- never called at S0
        judge_call=judge_approve,  # never called at S0 either
        expected_decision="reject",  # deliberately wrong
    )

    results = await run_self_test(scenarios=[deliberately_wrong_scenario])
    result = results[0]

    assert result.actual == "approve"
    assert result.expected == "reject"
    assert result.passed is False, "a genuine miss must be reported, never hidden as a pass"


async def test_summarize_never_filters_results_and_correctly_separates_missed():
    async def judge_approve(proposal, findings, objections):
        return GateVerdict(decision="approve", findings=findings, objections=objections, trace_id=str(proposal.proposal_id))

    clean = lambda proposal: Finding(validator="budget_check", claim="ok", evidence_state="verified_true", confidence=0.9)  # noqa: E731

    real_pass = AdversarialScenario(
        scenario_id="real_pass",
        description="x",
        proposal=ActionProposal(action_type=ActionType.CREATE_NOTE, payload={}, context_used=ContextSnapshot()),
        stakes=Stakes.S0,
        stage_a_checks=[clean],
        critic_call=lambda p, f: [],  # noqa: E731
        judge_call=judge_approve,
        expected_decision="approve",
    )
    real_miss = AdversarialScenario(
        scenario_id="real_miss",
        description="x",
        proposal=ActionProposal(action_type=ActionType.CREATE_NOTE, payload={}, context_used=ContextSnapshot()),
        stakes=Stakes.S0,
        stage_a_checks=[clean],
        critic_call=lambda p, f: [],  # noqa: E731
        judge_call=judge_approve,
        expected_decision="reject",
    )

    results = await run_self_test(scenarios=[real_pass, real_miss])
    summary = summarize(results, target="real_gate")

    assert summary.total == 2
    assert summary.caught == 1
    assert len(summary.missed) == 1
    assert summary.missed[0].scenario_id == "real_miss"
    assert len(summary.results) == 2, "results must never be filtered -- both scenarios present"
    assert summary.target == "real_gate"
