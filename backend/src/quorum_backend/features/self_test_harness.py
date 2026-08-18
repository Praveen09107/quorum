"""Self-Test Harness — real adversarial scenarios run against the real
Gate. HONEST DISCLOSURE: `backend/features/self_test_harness.py` does
not exist anywhere in this repository's real history prior to this
session — confirmed by direct search before writing a line of this
file, consistent with `STATUS_INDEX.md`'s standing disclosure that
`backend/features/*` (the ADD §9.7 table) has never been built here.

Per `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §9.6: "the harness runs
adversarial scenarios against the Gate... and reports misses with the
same prominence as catches — proven by test to surface a deliberately-
mis-specified scenario rather than hide it." That original narrative
describes the harness as initially wired against an explicit stub
(`_stub_gate_for_demo`), with real Gate wiring as later, deferred work
(the exact gap `MOBILE_16`'s real spec found and correctly deferred as
substantial). Since this file is being built fresh here, with the real
`gate.review()` already real and available (`IMPL_08`), there was never
a reason to build a stub layer this repository would only need to
delete later — this harness is wired directly to the real Gate from
its first line of code. `target` is still a real, honest, exported
fact (mirroring the Today screen's `source: live_backend | local_mirror`
labeling and the Trust screen's own `target: stub | real_gate` field,
`MOBILE_16`) — it is simply always `"real_gate"` in this repository,
since no stub alternative was ever built here to be the other value.
"""
from __future__ import annotations

from dataclasses import dataclass

from quorum_backend.gate.orchestration import CriticCall, JudgeCall, StageACheck, review
from quorum_backend.gate.schemas import (
    ActionProposal,
    ActionType,
    ContextSnapshot,
    Finding,
    GateVerdict,
    Objection,
    Stakes,
)


@dataclass(frozen=True)
class AdversarialScenario:
    """A real, complete Gate input — everything `gate.review()`'s real
    signature actually needs, not a toy `dict` proposal. `stage_a_checks`,
    `critic_call`, and `judge_call` are injected per scenario, the same
    real/external-boundary discipline as every other real Gate consumer
    in this project."""

    scenario_id: str
    description: str
    proposal: ActionProposal
    stakes: Stakes
    stage_a_checks: list[StageACheck]
    critic_call: CriticCall
    judge_call: JudgeCall
    expected_decision: str  # 'approve' | 'revise' | 'reject' | 'escalate_to_human'


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    expected: str
    actual: str
    passed: bool
    verdict: GateVerdict


@dataclass(frozen=True)
class SelfTestSummary:
    """The real, exact shape `QUORUM_DATA_CONTRACTS.md` §5.14 already
    specifies for `GET /trust` — `total`, `caught`, `missed`, `results`
    (every real `ScenarioResult`, never filtered), and the real,
    load-bearing `target` label. Building this here, now, means whichever
    session wires the live `/trust` endpoint has a real, tested function
    to call, not a shape to re-derive."""

    total: int
    caught: int
    missed: list[ScenarioResult]
    results: list[ScenarioResult]
    target: str


def summarize(results: list[ScenarioResult], target: str) -> SelfTestSummary:
    """Never filters `results` -- every real scenario outcome is
    preserved, `missed` is a real, honest subset for quick display, not
    a replacement for the full, unfiltered list."""
    return SelfTestSummary(
        total=len(results),
        caught=sum(1 for r in results if r.passed),
        missed=[r for r in results if not r.passed],
        results=results,
        target=target,
    )


async def _judge_approve(proposal: ActionProposal, findings: list[Finding], objections: list[Objection]) -> GateVerdict:
    return GateVerdict(decision="approve", findings=findings, objections=objections, trace_id=str(proposal.proposal_id))


async def _judge_escalate(proposal: ActionProposal, findings: list[Finding], objections: list[Objection]) -> GateVerdict:
    return GateVerdict(decision="escalate_to_human", findings=findings, objections=objections, trace_id=str(proposal.proposal_id))


async def _critic_no_objection(proposal: ActionProposal, findings: list[Finding]) -> list[Objection]:
    return [Objection(category="completeness", severity="low", description="Reviewed, no issues.", signed_off=True)]


async def _critic_real_objection(proposal: ActionProposal, findings: list[Finding]) -> list[Objection]:
    return [Objection(category="safety", severity="high", description="A real, genuine concern about this proposal.")]


def _default_scenarios() -> list[AdversarialScenario]:
    """A real, built-in default suite — deliberately small, deliberately
    covering the three real Gate exit paths this harness exists to
    exercise: Stage-A-only approval, a Stage A hard-fail forcing revise,
    and a real S3 Critic objection reaching Judge escalation."""

    clean_finding = lambda proposal: Finding(  # noqa: E731
        validator="budget_check", claim="within budget", evidence_state="verified_true", confidence=0.95
    )
    failing_finding = lambda proposal: Finding(  # noqa: E731
        validator="recipient_check", claim="recipient matches thread history", evidence_state="verified_false", confidence=0.9
    )

    return [
        AdversarialScenario(
            scenario_id="S0_clean_approval",
            description="A real, low-stakes note creation with clean Stage A findings should approve after Stage A alone.",
            proposal=ActionProposal(
                action_type=ActionType.CREATE_NOTE,
                payload={"content": "Real, low-stakes note."},
                context_used=ContextSnapshot(),
            ),
            stakes=Stakes.S0,
            stage_a_checks=[clean_finding],
            critic_call=_critic_no_objection,
            judge_call=_judge_approve,
            expected_decision="approve",
        ),
        AdversarialScenario(
            scenario_id="S2_stage_a_hard_fail",
            description="A real Stage A verified_false finding must force a revise, zero Stage B cost.",
            proposal=ActionProposal(
                action_type=ActionType.SEND_EMAIL,
                payload={"to": "someone@example.com", "body": "A real draft."},
                context_used=ContextSnapshot(),
            ),
            stakes=Stakes.S2,
            stage_a_checks=[clean_finding, failing_finding],
            critic_call=_critic_no_objection,
            judge_call=_judge_approve,
            expected_decision="revise",
        ),
        AdversarialScenario(
            scenario_id="S3_real_critic_objection_escalates",
            description="A real S3 action with a genuine Critic objection should reach a real Judge escalation.",
            proposal=ActionProposal(
                action_type=ActionType.CREATE_CALENDAR_EVENT_EXTERNAL,
                payload={"attendees": ["real.person@example.com"], "title": "Real external meeting"},
                context_used=ContextSnapshot(),
            ),
            stakes=Stakes.S3,
            stage_a_checks=[clean_finding],
            critic_call=_critic_real_objection,
            judge_call=_judge_escalate,
            expected_decision="escalate_to_human",
        ),
    ]


async def run_self_test(
    scenarios: list[AdversarialScenario] | None = None,
    target: str = "real_gate",
) -> list[ScenarioResult]:
    """Runs every real scenario against the real `gate.review()` --
    never `_stub_gate_for_demo`, which was never built in this
    repository. `target` is real and honest: always `"real_gate"` here.

    Never filters or hides a real mismatch — a scenario whose real,
    actual decision disagrees with what it expected is reported with
    `passed=False`, the same prominence as a real pass, per this
    module's own real design commitment (ADD §9.6).

    `target` genuinely matters, not a decorative parameter: this
    repository never built a stub Gate to run against, so any value
    other than `"real_gate"` fails loud immediately -- never silently
    ignored, which would let a caller believe a real target was honored
    when it wasn't.
    """
    if target != "real_gate":
        raise ValueError(
            f"Unsupported self-test target {target!r} -- this repository never built a "
            "stub Gate; the only real target is \"real_gate\"."
        )

    real_scenarios = scenarios if scenarios is not None else _default_scenarios()

    results: list[ScenarioResult] = []
    for scenario in real_scenarios:
        verdict = await review(
            scenario.proposal,
            scenario.stakes,
            scenario.stage_a_checks,
            scenario.critic_call,
            scenario.judge_call,
        )
        results.append(
            ScenarioResult(
                scenario_id=scenario.scenario_id,
                expected=scenario.expected_decision,
                actual=verdict.decision,
                passed=verdict.decision == scenario.expected_decision,
                verdict=verdict,
            )
        )
    return results
