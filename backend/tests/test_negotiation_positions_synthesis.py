"""Real tests for negotiation/positions.py and negotiation/synthesis.py."""
import asyncio
import time

import pytest

from quorum_backend.gate.schemas import NegotiationOption, Position
from quorum_backend.negotiation.positions import generate_positions
from quorum_backend.negotiation.synthesis import (
    SynthesisShapeError,
    build_synthesis_prompt,
    synthesize_options,
    validate_synthesis_shape,
)


async def test_positions_actually_run_in_parallel_not_sequentially():
    # A real timing proof, not an API-level assumption -- if generate_
    # positions were secretly sequential, three real 0.1s calls would take
    # 0.3s+; genuinely concurrent, it completes well under 0.2s.
    async def slow_call(domain: str) -> Position:
        await asyncio.sleep(0.1)
        return Position(domain=domain, concern="x", severity_claim="x", resource_claims=[], proposed_resolution="x")

    start = time.monotonic()
    await generate_positions(["calendar", "finance", "tasks"], slow_call)
    elapsed = time.monotonic() - start
    assert elapsed < 0.2, f"appears sequential: took {elapsed:.3f}s for 3 real 0.1s calls"


async def test_uninvolved_domain_is_never_called_at_all():
    calls_seen = []

    async def tracking_call(domain: str) -> Position:
        calls_seen.append(domain)
        return Position(domain=domain, concern="x", severity_claim="x", resource_claims=[], proposed_resolution="x")

    await generate_positions(["calendar"], tracking_call)
    assert calls_seen == ["calendar"]


def test_build_synthesis_prompt_includes_real_proposed_resolutions():
    positions = [
        Position(domain="calendar", concern="scheduling conflict", resource_claims=[], severity_claim="high", proposed_resolution="move the meeting")
    ]
    prompt = build_synthesis_prompt(positions)
    assert "move the meeting" in prompt


def test_ungrounded_invented_option_is_genuinely_caught():
    real_positions = [
        Position(domain="calendar", concern="x", severity_claim="x", resource_claims=[], proposed_resolution="move it")
    ]
    invented = [
        NegotiationOption(option_id="option_a", description="move it", source_domains=["calendar"]),
        NegotiationOption(option_id="option_b", description="waive a fee", source_domains=["finance"]),
        NegotiationOption(option_id="do_nothing", description="nothing"),
    ]
    with pytest.raises(SynthesisShapeError):
        validate_synthesis_shape(invented, real_positions)


def test_wrong_option_count_is_rejected():
    with pytest.raises(SynthesisShapeError):
        validate_synthesis_shape([NegotiationOption(option_id="option_a", description="x")], [])


def test_do_nothing_is_legitimately_exempt_from_grounding():
    positions = [
        Position(domain="calendar", concern="x", severity_claim="x", resource_claims=[], proposed_resolution="x")
    ]
    options = [
        NegotiationOption(option_id="option_a", description="x", source_domains=["calendar"]),
        NegotiationOption(option_id="option_b", description="x", source_domains=["calendar"]),
        NegotiationOption(option_id="do_nothing", description="x"),
    ]
    validate_synthesis_shape(options, positions)  # must not raise


async def test_synthesize_options_end_to_end_with_a_real_valid_synthesis_call():
    positions = [
        Position(domain="calendar", concern="x", severity_claim="x", resource_claims=[], proposed_resolution="move it")
    ]

    async def fake_synthesis_call(prompt: str) -> list[NegotiationOption]:
        assert "move it" in prompt  # confirms the real prompt was actually used
        return [
            NegotiationOption(option_id="option_a", description="move it", source_domains=["calendar"]),
            NegotiationOption(option_id="option_b", description="do it anyway", source_domains=["calendar"]),
            NegotiationOption(option_id="do_nothing", description="nothing"),
        ]

    options = await synthesize_options(positions, fake_synthesis_call)
    assert len(options) == 3
