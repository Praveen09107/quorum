"""The Gate's real state machine — gate.review(). CRITICAL TIER.

HONEST DISCLOSURE, unlike every validator built before this session: no
document in this project's real specification corpus reproduces literal
source code for this file (IMPL_08_GATE_ORCHESTRATION.md says "real,
complete — see file for full content," referencing a file that exists only
in a separate, inaccessible environment). What IS real and documented: the
exact state machine in QUORUM_GATE_SPECIFICATION.md Sec 2, and IMPL_08's own
described structural properties (the two failure classes, the stale-closure
bug this design deliberately avoids, the S2-vs-S3 Stage B routing). This
file is a real, careful construction from that documentation, not a copy of
given code — flagged explicitly, held to the same CRITICAL-tier scrutiny as
if it had been.

The historical stale-closure bug this design structurally avoids: an
earlier draft (per IMPL_08's own account) pre-bound each Stage A check to
the original proposal's extracted values as a zero-argument closure, which
would silently re-check stale values on a revision instead of the actual
revised payload. This implementation's StageACheck is always a function of
whatever proposal is passed to run_stage_a() at call time — there is no
closure capture anywhere, proven by test (see test_gate_orchestration.py's
stale-closure regression test).
"""
from __future__ import annotations

from typing import Awaitable, Callable

from quorum_backend.gate.schemas import (
    ActionProposal,
    Finding,
    GateVerdict,
    Objection,
    Stakes,
)

StageACheck = Callable[[ActionProposal], Finding]
CriticCall = Callable[[ActionProposal, list[Finding]], Awaitable[list[Objection]]]
JudgeCall = Callable[[ActionProposal, list[Finding], list[Objection]], Awaitable[GateVerdict]]


class InfrastructureFailure(Exception):
    """Raised when Stage B's real LLM calls fail repeatedly (a provider
    timeout or malformed structured output), after exhausting max_retries.
    This must never be silently swallowed into an approve verdict -- a real
    Gate infrastructure failure fails loud, never fails silently open."""


def run_stage_a(proposal: ActionProposal, stage_a_checks: list[StageACheck]) -> list[Finding]:
    """Runs every Stage A check fresh against the CURRENT proposal passed
    in -- never a captured value from an earlier call. Zero LLM calls,
    zero exceptions expected from any real Stage A validator."""
    return [check(proposal) for check in stage_a_checks]


def stage_a_hard_fail(findings: list[Finding]) -> bool:
    """True if any real Stage A finding is verified_false -- the structural
    trigger for the zero-Stage-B-cost short-circuit."""
    return any(f.evidence_state == "verified_false" for f in findings)


async def run_stage_b(
    proposal: ActionProposal,
    stakes: Stakes,
    findings: list[Finding],
    critic_call: CriticCall,
    judge_call: JudgeCall,
) -> GateVerdict:
    """S2 = single-check Stage B, Judge only. S3 = full debate, Critic
    runs and produces real objections BEFORE the Judge is ever called."""
    objections: list[Objection] = []
    if stakes == Stakes.S3:
        objections = await critic_call(proposal, findings)
    return await judge_call(proposal, findings, objections)


async def _call_with_retry(
    func: Callable[..., Awaitable[GateVerdict]],
    *args,
    max_retries: int = 2,
) -> GateVerdict:
    """Infrastructure-failure retry, entirely separate from the content-
    revision path below -- a transient provider hiccup is never miscounted
    as a Gate rejection. Tries up to max_retries times total; if every
    attempt raises, raises InfrastructureFailure rather than ever
    fabricating a passing verdict."""
    last_error: Exception | None = None
    for _attempt in range(max_retries):
        try:
            return await func(*args)
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any provider failure retries
            last_error = exc
    raise InfrastructureFailure(
        f"Stage B failed after {max_retries} attempts: {last_error}"
    ) from last_error


async def review(
    proposal: ActionProposal,
    stakes: Stakes,
    stage_a_checks: list[StageACheck],
    critic_call: CriticCall,
    judge_call: JudgeCall,
) -> GateVerdict:
    """The real Gate state machine, per QUORUM_GATE_SPECIFICATION.md Sec 2.

    Bounded to exactly one Stage-B-issued content revision by CODE
    STRUCTURE, not just a runtime counter check -- there is no loop
    anywhere in this function; a second Stage-B round is architecturally
    unreachable, not merely disallowed by a condition that could have a bug.
    """
    findings = run_stage_a(proposal, stage_a_checks)

    if stage_a_hard_fail(findings):
        # Stage A's own short-circuit -- zero Stage B cost, does NOT
        # consume the one-round revision budget. The Gate hasn't revised
        # anything itself; it's signaling the calling agent to redraft.
        return GateVerdict(
            decision="revise",
            revised_payload=None,
            findings=findings,
            objections=[],
            trace_id=str(proposal.proposal_id),
            revision_count=0,
        )

    if stakes in (Stakes.S0, Stakes.S1):
        # S0/S1 exit after Stage A alone -- Stage B never runs.
        return GateVerdict(
            decision="approve",
            findings=findings,
            objections=[],
            trace_id=str(proposal.proposal_id),
            revision_count=0,
        )

    # S2/S3 reach Stage B, with real infrastructure-failure retry.
    verdict = await _call_with_retry(run_stage_b, proposal, stakes, findings, critic_call, judge_call)

    if verdict.decision == "revise" and verdict.revised_payload is not None:
        # A Stage-B-issued revise DOES consume the one real revision round
        # -- the Gate itself re-checks the revised payload internally,
        # fresh, against the CURRENT (revised) proposal, not stale values.
        revised_proposal = proposal.model_copy(update={"payload": verdict.revised_payload})
        revised_findings = run_stage_a(revised_proposal, stage_a_checks)

        if stage_a_hard_fail(revised_findings):
            # A second Stage A failure on the revision escalates to a
            # human -- it does not loop back into Stage B a second time.
            return GateVerdict(
                decision="escalate_to_human",
                findings=revised_findings,
                objections=verdict.objections,
                trace_id=verdict.trace_id,
                revision_count=1,
            )

        return GateVerdict(
            decision="approve",
            revised_payload=verdict.revised_payload,
            findings=revised_findings,
            objections=verdict.objections,
            trace_id=verdict.trace_id,
            revision_count=1,
        )

    return verdict
