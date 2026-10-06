"""Real Gate execution timeline (`DEC-189` Block B).

WHY THIS EXISTS. A direct, confirmed product complaint drove the whole
rebuild this module belongs to: the app "is not currently an agentic AI
app, none of the AI features reflect in the app." The diagnosis behind
that, from a full read of the real code: **this system renders state and
never process.** Every screen shows a finished verdict. Nothing has ever
shown the Gate actually working.

`QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §12.1 had already named the
opposite as the thing this product should own -- *"a verification check
resolving is a real, literal, satisfying interaction, not a metaphor
buried in copy"* -- and `QUORUM_DATA_CONTRACTS.md` §5.3 specified
`GET /actions/{action_id}/status` with an incrementally-populated
`findings_so_far` to deliver it. That endpoint was never built. Neither
was any timing instrumentation of any kind: confirmed by direct search
before writing this file, there is not one `perf_counter`, not one stage
duration, and not one Langfuse call site anywhere in this backend. The
Gate has always been a black box that returns an answer.

THE DESIGN DECISION THAT MATTERS MOST HERE, and the reason this is a
separate module rather than edits to `orchestration.py`:
**`gate/orchestration.py` is not touched at all.** That file is
CRITICAL-tier, and its central correctness argument is structural --
"there is no loop anywhere in this function; a second Stage-B round is
architecturally unreachable, not merely disallowed by a condition that
could have a bug." Threading an observer through it would mean editing
the one function in this project whose safety comes from being small
enough to verify by reading. Instrumentation is not worth that risk.

So this module instruments the Gate from the OUTSIDE, by wrapping the
callables `review()` is already given: each `StageACheck`, the
`CriticCall`, and the `JudgeCall`. `review()` calls them exactly as
before and cannot tell the difference. Everything this module reports is
therefore observed at a real boundary, around a real call, with a real
`perf_counter` measurement -- never inferred, and never a number this
module made up.

WHAT THIS MODULE GUARANTEES, because it sits in the path of a real Gate
review and a real irreversible action may depend on that review
completing:

1. **It can never change a verdict.** The wrappers return exactly what
   they wrapped, unmodified. There is no branch anywhere in this file
   that depends on a finding's value.
2. **It can never fail a review.** Every sink call is wrapped in a bare
   `except Exception`. An observability bug must never be able to break
   the thing it observes. This is the one place in this project where
   swallowing an exception broadly is the correct choice rather than a
   smell, and it is deliberate.
3. **It never retains a model's raw output.** Only structural facts
   (names, states, counts, durations, decisions) and -- for the one
   genuinely product-critical case, the revision diff -- the payloads
   the Gate itself already persists to `action_events` anyway.
"""
from __future__ import annotations

import logging
from time import perf_counter
from typing import Callable

from quorum_backend.gate.orchestration import CriticCall, JudgeCall, StageACheck
from quorum_backend.gate.schemas import ActionProposal, Finding, GateVerdict, Objection, Stakes

logger = logging.getLogger("quorum_backend")

# A real, synchronous, non-blocking sink. Sync deliberately: a
# `StageACheck` is a sync callable (`Callable[[ActionProposal],
# Finding]`), so a wrapper around one genuinely cannot `await`. The live
# SSE route satisfies this with `asyncio.Queue.put_nowait`, which is a
# real sync method that is safe to call from the running event loop --
# so one sink type serves both the sync Stage A wrappers and the async
# Stage B ones, with no second code path to keep in step.
GateTimelineSink = Callable[[dict], None]


def emit_to_sink(sink: GateTimelineSink | None, record: dict) -> None:
    """Offers one record to a sink, never raising.

    This is the single place where this module's "observability must
    never break the thing it observes" promise is kept -- `GateTimeline.
    mark()` is its only caller, and that is deliberate: every event,
    whether from an instrumented Gate stage or marked explicitly by a
    caller, goes through `mark()` and therefore through here.

    HONEST NOTE ON WHY IT IS A SEPARATE FUNCTION AT ALL, since it has
    exactly one caller: an earlier version of this had non-Gate stages
    (extraction specifically) emitting straight to the sink, bypassing
    `GateTimeline`, which needed the same guarantee without going
    through `mark()`. That turned out to be a real defect rather than a
    design -- those events then had no shared clock and were never
    persisted (see `quick_capture.capture_action_from_text()` for the
    full account) -- and the fix routed them through `mark()` like
    everything else. It is kept as its own function because a bare
    `try/except Exception` inline in `mark()` would read as a smell
    rather than as the deliberate, documented choice it is.
    """
    if sink is None:
        return
    try:
        sink(record)
    except Exception:  # noqa: BLE001
        # See `GateTimeline.mark()` for the full reasoning: this runs
        # inside a real request that a real irreversible action may
        # depend on, and a closed client connection must never become a
        # failed capture.
        logger.warning("Timeline sink failed for event=%s -- pipeline continues unaffected", record.get("event"), exc_info=True)


class GateTimeline:
    """Records a real, measured timeline of one Gate review.

    Usage is deliberately explicit rather than implicit -- a caller
    wraps what it is about to hand to `review()`:

        timeline = GateTimeline()
        verdict = await review(
            proposal,
            stakes,
            timeline.instrument_stage_a(stage_a_checks),
            timeline.instrument_critic(critic_call),
            timeline.instrument_judge(judge_call),
        )
        timeline.finish(verdict, stakes)

    `finish()` is optional for the timing data -- every stage event is
    already recorded by then -- but it is what adds the real routing and
    outcome summary, so a caller that persists the timeline should call
    it.
    """

    def __init__(self, *, sink: GateTimelineSink | None = None) -> None:
        self._sink = sink
        self._events: list[dict] = []
        self._t0 = perf_counter()
        # Which pass of Stage A is running. `review()` runs Stage A a
        # second time after a Stage-B-issued revision, against the
        # revised proposal, and those two passes must be
        # distinguishable: showing a user eight check results without
        # saying four of them re-ran against a corrected payload would
        # misrepresent what the Gate actually did.
        self._stage_a_round = 0
        # The payload as it stood when the Judge was called, kept only
        # until we know whether the Judge revised it -- see
        # `pre_revision_payload`.
        self._payload_before_judge: dict | None = None
        self._pre_revision_payload: dict | None = None

    # -- recording ------------------------------------------------------

    def _elapsed_ms(self) -> int:
        return int((perf_counter() - self._t0) * 1000)

    def mark(self, event: str, **data: object) -> None:
        """Appends one real event and offers it to the sink.

        `at_ms` and `duration_ms` are deliberately both recorded where
        both are known. They answer genuinely different questions:
        `at_ms` (offset from the start of the review) is what orders a
        waterfall, and `duration_ms` is what a stage actually cost. A
        single "time" field would force the client to reconstruct one
        from the other and get it subtly wrong.
        """
        record = {"event": event, "at_ms": self._elapsed_ms(), **data}
        self._events.append(record)
        # Deliberately broad exception handling, and deliberately not
        # re-raised -- see `emit_to_sink()`, which owns that promise for
        # both this class and the non-Gate pipeline stages.
        emit_to_sink(self._sink, record)

    # -- instrumentation ------------------------------------------------

    def instrument_stage_a(self, checks: list[StageACheck]) -> list[StageACheck]:
        """Wraps each real Stage A check so its own name, three-valued
        result, confidence and real duration are recorded individually.

        Per-check rather than per-stage, deliberately: watching
        individual checks resolve one at a time is the entire interaction
        ADD §12.1 asked for, and a single aggregate "Stage A took 4ms"
        event could not produce it.

        The validator's name is read from the returned `Finding.
        validator`, NOT from the callable. That is not a shortcut -- it
        is the only correct source. Real callers build these checks as
        bare lambdas (`retry_queue_drainer.py::build_stage_a_checks_for_
        domain()`), so `__name__` is literally `"<lambda>"` for every
        one of them. The finding knows what produced it; the closure
        does not.

        ROUND DETECTION, and the one assumption this makes about code it
        does not own: a new Stage A pass is detected by index 0 being
        invoked again. That is reliable because `run_stage_a()` is a
        plain in-order list comprehension over this exact list, so index
        0 runs first in every pass. If that function ever became
        concurrent or reordered, this would need revisiting -- stated
        here rather than left as a silent dependency.
        """

        def wrap(index: int, check: StageACheck) -> StageACheck:
            def instrumented(proposal: ActionProposal) -> Finding:
                if index == 0:
                    self._stage_a_round += 1
                    self.mark("stage_a.start", round=self._stage_a_round, check_count=len(checks))
                started = perf_counter()
                try:
                    finding = check(proposal)
                except Exception as exc:  # noqa: BLE001
                    # A real Stage A validator is pure code and is not
                    # expected to raise (`orchestration.py`: "zero
                    # exceptions expected"). If one ever does, record
                    # that honestly and re-raise -- this module must
                    # never convert a genuine validator failure into a
                    # silent gap in the timeline, which would make the
                    # Gate look like it ran a check it did not.
                    self.mark(
                        "stage_a.check_error",
                        round=self._stage_a_round,
                        index=index,
                        error=type(exc).__name__,
                        duration_ms=int((perf_counter() - started) * 1000),
                    )
                    raise
                self.mark(
                    "stage_a.check",
                    round=self._stage_a_round,
                    index=index,
                    validator=finding.validator,
                    claim=finding.claim,
                    evidence_state=finding.evidence_state,
                    confidence=finding.confidence,
                    duration_ms=int((perf_counter() - started) * 1000),
                )
                return finding

            return instrumented

        return [wrap(i, check) for i, check in enumerate(checks)]

    def instrument_critic(self, critic_call: CriticCall) -> CriticCall:
        """Wraps the real Critic call.

        `attempt` is recorded because `orchestration.py::_call_with_
        retry()` wraps the whole of `run_stage_b`, so a transient
        provider failure genuinely re-runs the Critic AND the Judge. A
        timeline that showed two Critic events with no explanation would
        look like a bug in the Gate rather than what it is -- a real,
        correctly-handled infrastructure retry.

        `signed_off_count` is recorded alongside the raw count because
        an `Objection` with `signed_off=True` is the Critic's real "I
        reviewed this and found nothing" output, not an objection. The
        two genuinely differ and collapsing them would overstate how
        much the Critic pushed back.
        """
        attempt = 0

        async def instrumented(proposal: ActionProposal, findings: list[Finding]) -> list[Objection]:
            nonlocal attempt
            attempt += 1
            self.mark("stage_b.critic.start", attempt=attempt)
            started = perf_counter()
            try:
                objections = await critic_call(proposal, findings)
            except Exception as exc:  # noqa: BLE001
                self.mark(
                    "stage_b.critic.error",
                    attempt=attempt,
                    error=type(exc).__name__,
                    duration_ms=int((perf_counter() - started) * 1000),
                )
                raise
            self.mark(
                "stage_b.critic",
                attempt=attempt,
                objection_count=sum(1 for o in objections if not o.signed_off),
                signed_off_count=sum(1 for o in objections if o.signed_off),
                categories=sorted({o.category for o in objections if not o.signed_off}),
                highest_severity=_highest_severity(objections),
                duration_ms=int((perf_counter() - started) * 1000),
            )
            return objections

        return instrumented

    def instrument_judge(self, judge_call: JudgeCall) -> JudgeCall:
        """Wraps the real Judge call, and captures the pre-revision
        payload.

        THE PRE-REVISION PAYLOAD IS THE POINT OF THIS WRAPPER, beyond
        timing. "Here is what the AI wanted to send, and here is what
        the Gate made it change" is the single most compelling artifact
        this system can produce -- it is the thesis, demonstrated on
        real data rather than described. It has never been showable,
        because the revision is applied and the original is discarded in
        the same breath (`review()` builds `revised_proposal` from
        `verdict.revised_payload` and nothing retains what came before).

        This wrapper is the correct place to capture it, and the only
        clean one: the Judge is by construction the thing that issues a
        revision, so the payload as it stood on the way IN to this call
        is exactly the pre-revision payload, with no guessing about
        which branch `review()` took afterward.
        """
        attempt = 0

        async def instrumented(
            proposal: ActionProposal, findings: list[Finding], objections: list[Objection]
        ) -> GateVerdict:
            nonlocal attempt
            attempt += 1
            self.mark("stage_b.judge.start", attempt=attempt)
            # Captured before the call, so it is genuinely the payload
            # the Judge was asked to rule on. A real `dict(...)` copy,
            # not a reference -- `review()` does not mutate the payload
            # in place today, but a shallow copy costs nothing and means
            # this record cannot be invalidated by someone later
            # deciding that it should.
            self._payload_before_judge = dict(proposal.payload)
            started = perf_counter()
            try:
                verdict = await judge_call(proposal, findings, objections)
            except Exception as exc:  # noqa: BLE001
                self.mark(
                    "stage_b.judge.error",
                    attempt=attempt,
                    error=type(exc).__name__,
                    duration_ms=int((perf_counter() - started) * 1000),
                )
                raise
            revised = verdict.revised_payload is not None
            if revised:
                self._pre_revision_payload = self._payload_before_judge
            self.mark(
                "stage_b.judge",
                attempt=attempt,
                decision=verdict.decision,
                revised=revised,
                duration_ms=int((perf_counter() - started) * 1000),
            )
            if revised:
                self.mark(
                    "revision",
                    changed_keys=sorted(
                        _changed_keys(self._payload_before_judge or {}, verdict.revised_payload or {})
                    ),
                )
            return verdict

        return instrumented

    # -- completion -----------------------------------------------------

    def finish(self, verdict: GateVerdict, stakes: Stakes) -> None:
        """Records the real routing summary and final outcome.

        Called AFTER `review()` returns, deliberately, rather than
        guessed up front: `stage_b_ran` is derived from what was
        actually observed, not from what the stakes tier implies. Those
        two genuinely diverge -- an S2/S3 proposal whose Stage A hard-
        fails never reaches Stage B at all, and a timeline that claimed
        otherwise because the tier said S3 would be describing a code
        path that did not run.
        """
        self.mark(
            "done",
            decision=verdict.decision,
            stakes=stakes.value,
            revision_count=verdict.revision_count,
            stage_b_ran=any(e["event"] == "stage_b.judge" for e in self._events),
            stage_a_rounds=self._stage_a_round,
            finding_count=len(verdict.findings),
            objection_count=len(verdict.objections),
            trace_id=verdict.trace_id,
        )

    # -- accessors ------------------------------------------------------

    @property
    def events(self) -> list[dict]:
        """The recorded events, oldest first. A copy -- a consumer must
        not be able to mutate the record of what happened."""
        return list(self._events)

    @property
    def pre_revision_payload(self) -> dict | None:
        """The payload as the Judge received it, but ONLY when the Judge
        genuinely revised it. `None` otherwise, deliberately: returning
        the payload unconditionally would make every single action look
        like it had been corrected by the Gate, which is both false and
        exactly the kind of overstatement this project's honesty rules
        exist to prevent."""
        return self._pre_revision_payload

    @property
    def total_ms(self) -> int:
        return self._elapsed_ms()


def _highest_severity(objections: list[Objection]) -> str | None:
    """The most severe real objection's severity, ignoring sign-offs.
    `None` when the Critic genuinely raised nothing -- never a
    stand-in `"low"`, which would imply a real objection existed."""
    order = {"low": 0, "medium": 1, "high": 2}
    real = [o.severity for o in objections if not o.signed_off]
    if not real:
        return None
    return max(real, key=lambda s: order.get(s, 0))


def _changed_keys(before: dict, after: dict) -> set[str]:
    """Keys that genuinely differ between the two payloads, including
    keys added or removed. Compares values, not just key sets, so a
    revision that rewrites an email body is reported as a change rather
    than as nothing having happened."""
    return {key for key in (set(before) | set(after)) if before.get(key) != after.get(key)}
