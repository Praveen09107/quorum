"""Real option synthesis -- merge, not invent, mechanically enforced.
HONEST DISCLOSURE: construction-not-copy pattern, same as every
negotiation/Gate file.

The real engineering problem this file solves: letting a model combine
several real, independently-generated resolutions into something coherent,
without letting it quietly invent a solution grounded in nothing a domain
actually proposed. Two real mechanisms, not one hopeful prompt
instruction: build_synthesis_prompt only ever lists real proposed
resolutions, and validate_synthesis_shape mechanically checks every
synthesized option's source_domains against which domains actually
produced a real Position -- an option referencing a domain that never had
one is caught and raised by name, in code, not trusted to prompt phrasing
alone.
"""
from __future__ import annotations

from typing import Awaitable, Callable

from quorum_backend.gate.schemas import NegotiationOption, Position

SynthesisCall = Callable[[str], Awaitable[list[NegotiationOption]]]


class SynthesisShapeError(Exception):
    """Raised when synthesized options don't match the real, required
    shape -- exactly 2 real options plus one do_nothing, and every real
    option's source_domains genuinely grounded in an actual Position.
    This is the structural signature of invention, caught in code."""


def build_synthesis_prompt(positions: list[Position]) -> str:
    lines = [
        "Combine the following real domain proposals into exactly two "
        "complete options, plus a 'do nothing' option. Do not invent any "
        "resolution not already proposed below -- every option's "
        "source_domains must trace to a real proposal listed here."
    ]
    for p in positions:
        lines.append(f"- {p.domain}: {p.concern} -- proposed resolution: {p.proposed_resolution}")
    return "\n".join(lines)


def validate_synthesis_shape(options: list[NegotiationOption], positions: list[Position]) -> None:
    if len(options) != 3:
        raise SynthesisShapeError(
            f"Expected exactly 3 options (2 real + do_nothing), got {len(options)}"
        )

    non_do_nothing = [o for o in options if o.option_id != "do_nothing"]
    if len(non_do_nothing) != 2:
        raise SynthesisShapeError(
            f"Expected exactly 2 non-do_nothing options, got {len(non_do_nothing)}"
        )

    real_domains = {p.domain for p in positions}
    for option in non_do_nothing:
        for domain in option.source_domains:
            if domain not in real_domains:
                raise SynthesisShapeError(
                    f"Option {option.option_id!r} references domain {domain!r}, "
                    "which never produced a real Position -- invented, not merged"
                )


async def synthesize_options(
    positions: list[Position],
    synthesis_call: SynthesisCall,
) -> list[NegotiationOption]:
    prompt = build_synthesis_prompt(positions)
    options = await synthesis_call(prompt)
    validate_synthesis_shape(options, positions)
    return options
