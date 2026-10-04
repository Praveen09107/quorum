"""Real tests for gate/timeline.py (`DEC-189` Block B).

Entirely pure -- no database, no LLM, no network. The whole point of
instrumenting the Gate from the outside (by wrapping the callables
`review()` is handed, rather than editing `review()` itself) is that the
instrumentation is testable in isolation AND that the real state machine
is provably unaffected. Several tests below exist specifically to prove
the second half of that.
"""
import pytest

from quorum_backend.gate.orchestration import review
from quorum_backend.gate.schemas import ActionProposal, ActionType, Finding, GateVerdict, Objection, Stakes
from quorum_backend.gate.timeline import GateTimeline, emit_to_sink


def _proposal(**payload) -> ActionProposal:
    return ActionProposal(action_type=ActionType.CREATE_TASK, payload=payload or {"title": "x"})


def _finding(validator: str, state: str = "verified_true", confidence: float = 0.9) -> Finding:
    return Finding(validator=validator, claim=f"{validator} says so", evidence_state=state, confidence=confidence)


def _objection(severity: str = "medium", *, signed_off: bool = False, category: str = "tone") -> Objection:
    return Objection(category=category, severity=severity, description="d", signed_off=signed_off)


# --- Stage A instrumentation ---


def test_instrument_stage_a_records_one_event_per_check_with_the_real_validator_name():
    """The validator name must come from the returned `Finding`, not the
    callable: real callers build these checks as bare lambdas
    (`build_stage_a_checks_for_domain()`), so `__name__` is literally
    `"<lambda>"` for every one of them."""
    timeline = GateTimeline()
    checks = [lambda p: _finding("provenance_check"), lambda p: _finding("deadline_conflict_check")]

    instrumented = timeline.instrument_stage_a(checks)
    findings = [check(_proposal()) for check in instrumented]

    assert [f.validator for f in findings] == ["provenance_check", "deadline_conflict_check"]
    check_events = [e for e in timeline.events if e["event"] == "stage_a.check"]
    assert [e["validator"] for e in check_events] == ["provenance_check", "deadline_conflict_check"]
    assert all("duration_ms" in e and "at_ms" in e for e in check_events)
    assert all(e["evidence_state"] == "verified_true" for e in check_events)


def test_instrument_stage_a_returns_the_exact_finding_it_wrapped():
    """The single most important safety property of this whole module:
    instrumentation must be incapable of changing a verdict. If the
    wrapper returned anything other than the identical Finding object,
    it would be sitting in the decision path."""
    timeline = GateTimeline()
    original = _finding("provenance_check", "verified_false")
    wrapped = timeline.instrument_stage_a([lambda p: original])[0]

    assert wrapped(_proposal()) is original


def test_instrument_stage_a_distinguishes_the_two_real_stage_a_rounds():
    """`review()` runs Stage A a SECOND time against the revised
    proposal after a Stage-B revision. Showing a user eight results
    without saying four of them re-ran against a corrected payload would
    misrepresent what the Gate actually did."""
    timeline = GateTimeline()
    checks = [lambda p: _finding("a"), lambda p: _finding("b")]
    instrumented = timeline.instrument_stage_a(checks)

    for _round in range(2):
        for check in instrumented:
            check(_proposal())

    rounds = [e["round"] for e in timeline.events if e["event"] == "stage_a.check"]
    assert rounds == [1, 1, 2, 2]
    starts = [e for e in timeline.events if e["event"] == "stage_a.start"]
    assert [s["round"] for s in starts] == [1, 2]
    assert all(s["check_count"] == 2 for s in starts)


def test_instrument_stage_a_records_and_reraises_a_validator_that_raises():
    """A real Stage A validator is pure code and is not expected to
    raise. If one ever does, the timeline must say so and the exception
    must still propagate -- silently swallowing it would make the Gate
    look like it ran a check it did not."""
    timeline = GateTimeline()

    def boom(p):
        raise RuntimeError("validator exploded")

    wrapped = timeline.instrument_stage_a([boom])[0]

    with pytest.raises(RuntimeError, match="validator exploded"):
        wrapped(_proposal())

    errors = [e for e in timeline.events if e["event"] == "stage_a.check_error"]
    assert len(errors) == 1
    assert errors[0]["error"] == "RuntimeError"


# --- Critic instrumentation ---


async def test_instrument_critic_counts_real_objections_separately_from_sign_offs():
    """An `Objection` with `signed_off=True` is the Critic's real "I
    reviewed this and found nothing" output, not an objection. Collapsing
    the two would overstate how much the Critic pushed back."""
    timeline = GateTimeline()
    objections = [_objection("high"), _objection("low"), _objection(signed_off=True)]

    async def critic(p, f):
        return objections

    result = await timeline.instrument_critic(critic)(_proposal(), [])

    assert result is objections  # returns exactly what it wrapped
    event = next(e for e in timeline.events if e["event"] == "stage_b.critic")
    assert event["objection_count"] == 2
    assert event["signed_off_count"] == 1
    assert event["highest_severity"] == "high"


async def test_instrument_critic_reports_no_severity_when_nothing_was_raised():
    """`None`, never a stand-in `"low"` -- a floor value would imply a
    real objection existed when none did."""
    timeline = GateTimeline()

    async def critic(p, f):
        return [_objection(signed_off=True)]

    await timeline.instrument_critic(critic)(_proposal(), [])

    event = next(e for e in timeline.events if e["event"] == "stage_b.critic")
    assert event["highest_severity"] is None
    assert event["objection_count"] == 0


async def test_instrument_critic_counts_attempts_so_a_real_retry_is_not_read_as_a_bug():
    """`_call_with_retry()` wraps the whole of `run_stage_b`, so a
    transient provider failure genuinely re-runs the Critic. Two Critic
    events with no explanation would look like a Gate bug rather than a
    correctly-handled infrastructure retry."""
    timeline = GateTimeline()
    calls = 0

    async def flaky(p, f):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("provider hiccup")
        return []

    instrumented = timeline.instrument_critic(flaky)
    with pytest.raises(TimeoutError):
        await instrumented(_proposal(), [])
    await instrumented(_proposal(), [])

    assert [e["attempt"] for e in timeline.events if e["event"] == "stage_b.critic.error"] == [1]
    assert [e["attempt"] for e in timeline.events if e["event"] == "stage_b.critic"] == [2]


# --- Judge instrumentation and the pre-revision payload ---


async def test_instrument_judge_captures_the_pre_revision_payload_only_when_revised():
    """THE artifact this column exists for: "here is what the AI wanted
    to send, and here is what the Gate made it change." `review()` builds
    the revised proposal and nothing retains what came before, so this
    was previously unshowable."""
    timeline = GateTimeline()

    async def judge(p, f, o):
        return GateVerdict(
            decision="revise",
            revised_payload={"title": "Corrected", "hours": 2},
            findings=[],
            objections=[],
            trace_id="t",
            revision_count=0,
        )

    await timeline.instrument_judge(judge)(_proposal(title="Original", hours=2), [], [])

    assert timeline.pre_revision_payload == {"title": "Original", "hours": 2}
    revision = next(e for e in timeline.events if e["event"] == "revision")
    # Only the key that genuinely differs -- `hours` was unchanged.
    assert revision["changed_keys"] == ["title"]


async def test_instrument_judge_leaves_pre_revision_payload_none_when_not_revised():
    """Returning the payload unconditionally would make every single
    action look like the Gate had corrected it -- false, and exactly the
    kind of overstatement this project's honesty rules forbid."""
    timeline = GateTimeline()

    async def judge(p, f, o):
        return GateVerdict(decision="approve", findings=[], objections=[], trace_id="t", revision_count=0)

    await timeline.instrument_judge(judge)(_proposal(title="Original"), [], [])

    assert timeline.pre_revision_payload is None
    assert not [e for e in timeline.events if e["event"] == "revision"]


async def test_instrument_judge_returns_the_exact_verdict_it_wrapped():
    timeline = GateTimeline()
    verdict = GateVerdict(decision="approve", findings=[], objections=[], trace_id="t", revision_count=0)

    async def judge(p, f, o):
        return verdict

    assert await timeline.instrument_judge(judge)(_proposal(), [], []) is verdict


# --- the sink ---


def test_a_failing_sink_can_never_break_a_review():
    """The load-bearing guarantee. This sits inside a real Gate review
    that a real irreversible action may depend on; a closed client
    connection or a full queue must never turn a successful
    verification into an error."""
    def exploding_sink(record):
        raise RuntimeError("client disconnected")

    timeline = GateTimeline(sink=exploding_sink)
    wrapped = timeline.instrument_stage_a([lambda p: _finding("provenance_check")])[0]

    finding = wrapped(_proposal())  # must not raise

    assert finding.validator == "provenance_check"
    # The event is still recorded internally even though the sink died,
    # so the persisted timeline is complete regardless of the stream.
    assert any(e["event"] == "stage_a.check" for e in timeline.events)


def test_emit_to_sink_tolerates_a_none_sink_and_a_failing_one():
    emit_to_sink(None, {"event": "x"})  # must not raise

    def boom(record):
        raise ValueError("nope")

    emit_to_sink(boom, {"event": "x"})  # must not raise


def test_the_sink_receives_events_in_real_time_as_each_check_resolves():
    """Streaming is the whole point -- a sink that only saw everything
    at the end could not drive a live UI."""
    seen = []
    timeline = GateTimeline(sink=seen.append)
    instrumented = timeline.instrument_stage_a([lambda p: _finding("a"), lambda p: _finding("b")])

    instrumented[0](_proposal())
    after_first = [e["event"] for e in seen]
    instrumented[1](_proposal())

    assert after_first == ["stage_a.start", "stage_a.check"]
    assert [e["event"] for e in seen] == ["stage_a.start", "stage_a.check", "stage_a.check"]


def test_events_property_returns_a_copy_so_a_consumer_cannot_rewrite_history():
    timeline = GateTimeline()
    timeline.mark("done", decision="approve")
    timeline.events.clear()
    assert len(timeline.events) == 1


# --- finish() ---


def test_finish_derives_stage_b_ran_from_observation_not_from_the_stakes_tier():
    """These genuinely diverge: an S3 proposal whose Stage A hard-fails
    never reaches Stage B at all. A timeline claiming otherwise because
    the tier said S3 would describe a code path that did not run."""
    timeline = GateTimeline()
    verdict = GateVerdict(
        decision="revise", findings=[_finding("x", "verified_false")], objections=[], trace_id="t", revision_count=0
    )

    timeline.finish(verdict, Stakes.S3)

    done = next(e for e in timeline.events if e["event"] == "done")
    assert done["stakes"] == "S3"
    assert done["stage_b_ran"] is False


# --- end to end against the REAL state machine ---


async def test_the_real_review_state_machine_is_unaffected_by_instrumentation():
    """Runs the genuine `gate.orchestration.review()` twice over the same
    inputs -- once bare, once fully instrumented -- and asserts the real
    verdicts are identical. This is the proof that matters: not that the
    timeline records correctly, but that recording it changed nothing
    about the Gate's own decision.
    """
    def make_inputs():
        checks = [lambda p: _finding("provenance_check"), lambda p: _finding("coverage_check", "no_data_found")]

        async def critic(p, f):
            return [_objection("medium")]

        async def judge(p, f, o):
            return GateVerdict(
                decision="revise",
                revised_payload={"title": "Tightened"},
                findings=f,
                objections=o,
                trace_id="trace-1",
                revision_count=0,
            )

        return checks, critic, judge

    proposal = _proposal(title="Original")

    checks, critic, judge = make_inputs()
    bare = await review(proposal, Stakes.S3, checks, critic, judge)

    checks, critic, judge = make_inputs()
    timeline = GateTimeline()
    instrumented = await review(
        proposal,
        Stakes.S3,
        timeline.instrument_stage_a(checks),
        timeline.instrument_critic(critic),
        timeline.instrument_judge(judge),
    )

    assert instrumented.decision == bare.decision
    assert instrumented.revised_payload == bare.revised_payload
    assert instrumented.revision_count == bare.revision_count
    assert [f.validator for f in instrumented.findings] == [f.validator for f in bare.findings]
    assert [o.description for o in instrumented.objections] == [o.description for o in bare.objections]

    # And the timeline genuinely captured the full real shape: a real
    # revision means Stage A ran twice and the pre-revision payload was
    # retained.
    timeline.finish(instrumented, Stakes.S3)
    done = next(e for e in timeline.events if e["event"] == "done")
    assert done["stage_a_rounds"] == 2
    assert done["revision_count"] == 1
    assert done["stage_b_ran"] is True
    assert timeline.pre_revision_payload == {"title": "Original"}


def test_timeline_events_are_json_serializable():
    """They are written straight into a real JSONB column."""
    import json

    timeline = GateTimeline()
    wrapped = timeline.instrument_stage_a([lambda p: _finding("provenance_check")])[0]
    wrapped(_proposal())
    json.dumps(timeline.events)  # must not raise
