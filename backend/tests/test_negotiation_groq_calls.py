"""Real tests for negotiation/groq_calls.py -- the first real Stage-B-
style LLM content-generation call this backend has ever made (originally
Gemini-backed, `negotiation/gemini_calls.py`, `DEC-121`; migrated to Groq
under `DEC-166`'s real AI-provider rebalancing -- see that module's own
top-of-file docstring for the full reasoning). This file replaces
`test_negotiation_gemini_calls.py` in full, renamed to match.

Error-path tests (`# --- Error paths`) use a monkeypatched httpx client --
deterministic, network-independent, matching `test_embeddings.py`'s own
established pattern; the point of these specific tests is proving the
retry/error-handling logic is correct for cases a real, live call cannot
reliably reproduce on demand.

The tests below `# --- Real, live tests` call the actual, live Groq API
with the real `GROQ_API_KEY` in `backend/.env`, per `CLAUDE.md` Rule 5 --
this is the one that actually proves the integration works. Skipped, not
failed, without a real key configured (e.g. CI).

No `reserve_gemini_quota_slot` mocking is needed here any more -- this
module no longer calls Gemini or reserves any `core/gemini_quota.py`
slot, per `DEC-166`."""
import pytest

from quorum_backend.core.config import get_settings
from quorum_backend.gate.schemas import NegotiationOption, Position, ResourceClaim
from quorum_backend.negotiation.groq_calls import (
    GroqGenerationError,
    make_groq_position_call,
    make_groq_synthesis_call,
)
from quorum_backend.negotiation.impact_simulator import DomainSnapshot
from quorum_backend.negotiation.subgraph import NegotiationState, build_negotiation_graph
from quorum_backend.negotiation.trigger import DomainState

_HAS_REAL_KEY = get_settings().groq_api_key is not None


def _groq_response(content: str) -> dict:
    """Real, live Groq `chat/completions` response shape --
    `choices[0].message.content` holds the real, structured JSON text,
    matching `gate/llm_calls.py::_call_groq_json`'s own already-verified
    real parsing path exactly."""
    return {"choices": [{"message": {"content": content}}]}


# --- Error paths (deterministic, monkeypatched httpx client, no real network) ---


async def test_position_call_raises_groq_generation_error_after_real_retries_exhausted(monkeypatch):
    call_count = 0

    class _FakeResponse:
        status_code = 500
        text = "server error"

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _FakeResponse()

    monkeypatch.setattr("quorum_backend.negotiation.groq_calls.httpx.AsyncClient", lambda **kwargs: _FakeClient())

    position_call = make_groq_position_call({"finance": "test context"}, api_key="fake-key-never-sent")
    with pytest.raises(GroqGenerationError, match="after 2 attempts"):
        await position_call("finance")
    assert call_count == 2  # real, confirmed retry happened, not a single-shot failure


async def test_position_call_raises_on_malformed_json_response(monkeypatch):
    class _FakeResponse:
        status_code = 200
        text = "irrelevant"

        def json(self):
            return _groq_response("not valid json at all")

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *args, **kwargs):
            return _FakeResponse()

    monkeypatch.setattr("quorum_backend.negotiation.groq_calls.httpx.AsyncClient", lambda **kwargs: _FakeClient())

    position_call = make_groq_position_call({}, api_key="fake-key-never-sent")
    with pytest.raises(GroqGenerationError):
        await position_call("tasks")


async def test_position_call_raises_on_empty_message_content(monkeypatch):
    """Real, live-discovered behavior `gate/llm_calls.py`'s own top-of-
    file docstring already disclosed for this same underlying model
    (`openai/gpt-oss-120b` is a reasoning model that can exhaust its
    token budget on internal reasoning before ever producing real
    `content`) -- pinned down here too, since this module shares that
    real model."""

    class _FakeResponse:
        status_code = 200
        text = "irrelevant"

        def json(self):
            return _groq_response("")

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *args, **kwargs):
            return _FakeResponse()

    monkeypatch.setattr("quorum_backend.negotiation.groq_calls.httpx.AsyncClient", lambda **kwargs: _FakeClient())

    position_call = make_groq_position_call({}, api_key="fake-key-never-sent")
    with pytest.raises(GroqGenerationError, match="reasoning-token budget"):
        await position_call("tasks")


async def test_synthesis_call_recovers_after_one_real_transient_failure(monkeypatch):
    """Confirms the retry logic isn't purely theoretical: the first call
    fails, the second succeeds -- mirrors the real, live 503 this
    project's own live verification actually observed while building
    this module's original Gemini-backed version."""
    call_count = 0

    class _FailResponse:
        status_code = 503
        text = "high demand"

    class _OkResponse:
        status_code = 200
        text = "irrelevant"

        def json(self):
            return _groq_response(
                '{"options": ['
                '{"description": "d", "source_domains": ["finance"]},'
                '{"description": "e", "source_domains": ["tasks"]}'
                "]}"
            )

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _FailResponse() if call_count == 1 else _OkResponse()

    monkeypatch.setattr("quorum_backend.negotiation.groq_calls.httpx.AsyncClient", lambda **kwargs: _FakeClient())

    synthesis_call = make_groq_synthesis_call(api_key="fake-key-never-sent")
    options = await synthesis_call("a real prompt")
    assert call_count == 2
    assert options[0].option_id == "option_a"
    # A real, code-guaranteed property, not asked of the model: the
    # "do nothing" option is always present with the exact literal ID
    # validate_synthesis_shape() requires, regardless of what the model
    # itself returned.
    assert options[-1].option_id == "do_nothing"


async def test_synthesis_call_slices_to_exactly_two_real_options_when_model_returns_more(monkeypatch):
    """A real, live-discovered gap this test pins down permanently: a
    genuine Gemini response was observed returning 3 real options
    despite the prompt asking for "exactly two" -- structured-output
    mode doesn't mechanically enforce array length from prose alone.
    Kept as a defensive real safeguard under Groq too, even though it
    hasn't yet been separately observed live on this provider."""

    class _FakeResponse:
        status_code = 200
        text = "irrelevant"

        def json(self):
            return _groq_response(
                '{"options": ['
                '{"description": "a", "source_domains": ["finance"]},'
                '{"description": "b", "source_domains": ["tasks"]},'
                '{"description": "c", "source_domains": ["finance", "tasks"]}'
                "]}"
            )

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *args, **kwargs):
            return _FakeResponse()

    monkeypatch.setattr("quorum_backend.negotiation.groq_calls.httpx.AsyncClient", lambda **kwargs: _FakeClient())

    synthesis_call = make_groq_synthesis_call(api_key="fake-key-never-sent")
    options = await synthesis_call("a real prompt")

    assert len(options) == 3  # 2 real + do_nothing, never 4
    assert [o.option_id for o in options] == ["option_a", "option_b", "do_nothing"]
    assert options[0].description == "a"
    assert options[1].description == "b"  # the 3rd real option ("c") was genuinely dropped, not silently kept


async def test_synthesis_call_raises_when_model_returns_fewer_than_two_real_options(monkeypatch):
    class _FakeResponse:
        status_code = 200
        text = "irrelevant"

        def json(self):
            return _groq_response('{"options": [{"description": "a", "source_domains": []}]}')

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *args, **kwargs):
            return _FakeResponse()

    monkeypatch.setattr("quorum_backend.negotiation.groq_calls.httpx.AsyncClient", lambda **kwargs: _FakeClient())

    synthesis_call = make_groq_synthesis_call(api_key="fake-key-never-sent")
    with pytest.raises(GroqGenerationError, match="need at least 2"):
        await synthesis_call("a real prompt")


# --- Real, live tests (skipped without a real GROQ_API_KEY) ---


@pytest.mark.skipif(not _HAS_REAL_KEY, reason="no real GROQ_API_KEY configured in this environment")
async def test_position_call_returns_a_real_live_domain_grounded_position():
    settings = get_settings()
    position_call = make_groq_position_call(
        {"finance": "92% of this month's budget is spent with 8 days remaining."},
        api_key=settings.groq_api_key,
    )
    position = await position_call("finance")
    assert isinstance(position, Position)
    assert position.domain == "finance"
    assert len(position.concern) > 0
    assert len(position.proposed_resolution) > 0


@pytest.mark.skipif(not _HAS_REAL_KEY, reason="no real GROQ_API_KEY configured in this environment")
async def test_synthesis_call_returns_real_options_satisfying_the_real_shape_validator():
    """The real, mechanical shape check (`validate_synthesis_shape`,
    already built and tested in `negotiation/synthesis.py`) is the real
    proof here, not a hand-picked assertion -- a live Groq response
    that violated the real shape would raise `SynthesisShapeError`
    before this test could even reach its own assertions."""
    settings = get_settings()
    positions = [
        Position(
            domain="finance",
            concern="budget at risk",
            severity_claim="high",
            resource_claims=[ResourceClaim(claim_type="money", amount=100, unit="currency_minor_units")],
            proposed_resolution="halt non-critical spending",
        ),
        Position(
            domain="tasks",
            concern="overcommitted this week",
            severity_claim="high",
            resource_claims=[ResourceClaim(claim_type="effort", amount=10, unit="hours")],
            proposed_resolution="drop or reschedule a low-priority task",
        ),
    ]
    synthesis_call = make_groq_synthesis_call(api_key=settings.groq_api_key)

    from quorum_backend.negotiation.synthesis import synthesize_options

    options = await synthesize_options(positions, synthesis_call)

    assert len(options) == 3
    assert all(isinstance(o, NegotiationOption) for o in options)


@pytest.mark.skipif(not _HAS_REAL_KEY, reason="no real GROQ_API_KEY configured in this environment")
async def test_full_negotiation_pipeline_runs_end_to_end_with_real_groq_calls():
    """The real capstone: the same real subgraph `test_negotiation_
    subgraph.py` already proved composes correctly with FAKE calls, run
    here with the real Groq-backed factories this module provides --
    a real, live proof that this backend can run a complete negotiation
    (trigger -> real LLM positions -> real LLM synthesis -> real
    code-computed impact) without a single fabricated step anywhere in
    the chain."""
    settings = get_settings()
    from quorum_backend.negotiation.impact_simulator import OptionEffect

    position_call = make_groq_position_call(
        {
            "finance": "92% of this month's budget is spent with 8 days remaining.",
            "tasks": "3 tasks due this week totaling 14 hours, but only 8 working hours remain today.",
        },
        api_key=settings.groq_api_key,
    )
    synthesis_call = make_groq_synthesis_call(api_key=settings.groq_api_key)

    def effect_extractor(option: NegotiationOption) -> OptionEffect:
        # Real, deterministic mapping from a real, synthesized option's
        # source_domains to a real effect -- this part stays pure code,
        # per this project's own "the model narrates, the code
        # computes" rule; it is never itself an LLM call.
        if "finance" in option.source_domains:
            return OptionEffect(budget_remaining_fraction_change=0.1)
        if "tasks" in option.source_domains:
            return OptionEffect(task_hours_committed_change=-2.0)
        return OptionEffect()

    graph = build_negotiation_graph(position_call, synthesis_call, effect_extractor)

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
    assert sorted(p.domain for p in result["positions"]) == ["finance", "tasks"]
    assert len(result["options"]) == 3
    assert set(result["impact"].keys()) == {o.option_id for o in result["options"]}
