"""Real, live Gemini-backed `PositionCall`/`SynthesisCall` implementations
-- the first real Stage-B-style LLM content-generation call this backend
has ever made. `core/embeddings.py` (Roadmap Phase 4a) was the first real
outbound Gemini call of any kind; this module is the first one that
generates real natural-language content rather than a vector, and the
first real implementation of the negotiation subgraph's own injected
`PositionCall`/`SynthesisCall` types (`negotiation/positions.py`,
`negotiation/synthesis.py`) -- both have existed since `IMPL_18`/`IMPL_19`
as pure type signatures with zero real implementation anywhere in this
repository, confirmed by direct search before writing this file.

THE REAL MODEL, confirmed live before hardcoding it, the same discipline
`core/embeddings.py` already established: `gemini-2.5-flash` (a
plausible first guess, and the model this project's own real production
Stage A/B design docs would have named at the time they were written)
returned a real, live 404 -- not a missing-model 404, a real, informative
one: `"This model models/gemini-2.5-flash is no longer available to new
users. Please update your code to use models/gemini-3.6-flash..."`.
`gemini-3.6-flash` is what's actually used, confirmed live returning a
real, valid response.

STRUCTURED OUTPUT, not free-text-then-regex-parse: Gemini's real
`generationConfig.responseMimeType: "application/json"` plus a real
`responseSchema` were confirmed live, twice, before this module trusted
them -- once for `Position`'s object shape, once for the array-of-options
shape `synthesize_options()` needs. A real, live 503 ("high demand")
was also observed during that same verification pass, confirming the
retry logic below isn't defensive-for-its-own-sake -- it's handling a
failure mode this model provider genuinely produces.

RETRY DISCIPLINE, deliberately separate from `gate/orchestration.py`'s
own `_call_with_retry`: that function is typed specifically for Stage B's
`CriticCall`/`JudgeCall` shape (`Awaitable[GateVerdict]`); this module's
two call types return different real shapes (`Position`, `list[
NegotiationOption]`), so a small, local retry helper is used instead of
forcing an artificial shared abstraction across two genuinely different
call signatures. Same real principle both places: a transient provider
failure retries; every attempt failing raises loud, never fabricates a
plausible-looking result.
"""
from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable

import httpx

from quorum_backend.gate.schemas import NegotiationOption, Position

GEMINI_GENERATION_MODEL = "gemini-3.6-flash"

_GENERATE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_GENERATION_MODEL}:generateContent"


class GeminiGenerationError(Exception):
    """Raised when a real Gemini generateContent call -- and every real
    retry of it -- fails. Never silently substituted with an invented
    Position/NegotiationOption, which would be the exact "model
    fabricates, code doesn't verify" failure this project's whole Gate
    architecture exists to prevent."""


async def _call_gemini_json(prompt: str, *, response_schema: dict, api_key: str, max_retries: int = 2) -> dict:
    """Real, live call to Gemini's `generateContent`, structured JSON
    output, with real retry on transient failure. Returns the already-
    parsed real JSON body -- callers validate/construct real Pydantic
    objects from it, never trust it blindly.

    A REAL, DISCLOSED FIX, found by `features/negotiation_detail_
    backfill.py`'s own CRITICAL-tier review (`DEC-135`): this retry loop
    previously had no real delay between attempts at all -- harmless for
    a single, human-triggered call (`scripts/seed_demo_dataset.py`), but
    that module is the first real, autonomous, REPEATING caller this
    function has ever had, and a real `429` rate-limit response answered
    with an immediate, undelayed retry doubles the real request rate
    into the same limit that just rejected it. A short, real, linear
    backoff (`attempt` seconds before the `attempt`-th retry) is enough
    for this one real call site -- not elaborate exponential/jitter
    machinery this small a `max_retries` doesn't need."""
    last_error: Exception | None = None
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
        },
    }
    for attempt in range(max_retries):
        if attempt > 0:
            await asyncio.sleep(attempt)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(_GENERATE_URL, headers={"x-goog-api-key": api_key}, json=body)
            if response.status_code != 200:
                last_error = GeminiGenerationError(f"Gemini generateContent returned {response.status_code}")
                continue
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            last_error = exc
    raise GeminiGenerationError(f"Gemini generateContent failed after {max_retries} attempts: {last_error}") from last_error


_POSITION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "concern": {"type": "STRING"},
        "severity_claim": {"type": "STRING"},
        "proposed_resolution": {"type": "STRING"},
    },
    "required": ["concern", "severity_claim", "proposed_resolution"],
}

_SYNTHESIS_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "options": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "description": {"type": "STRING"},
                    "source_domains": {"type": "ARRAY", "items": {"type": "STRING"}},
                },
                "required": ["description", "source_domains"],
            },
        }
    },
    "required": ["options"],
}

# The real, live, literal ID `validate_synthesis_shape()` (`negotiation/
# synthesis.py`) requires for the always-present "do nothing" option --
# never asked of the model at all, for a real, live-discovered reason: a
# first version of this module DID ask Gemini for `option_id`, and a
# genuine, live response returned `"option_do_nothing"` instead of the
# exact literal `"do_nothing"` the validator checks for via `!=`,
# failing real, downstream shape validation on a real API response, not
# a hypothetical one. "Do nothing" is a fixed, code-known concept with
# no real creative content -- assigning its ID (and every other option's
# ID) deterministically in code removes this failure mode completely,
# rather than hoping a future prompt tweak keeps the model naming things
# exactly right. A closer, not looser, reading of "the model narrates,
# the code computes" -- structure and IDs are code's job here too, not
# just arithmetic.
_DO_NOTHING_OPTION_ID = "do_nothing"


def make_gemini_position_call(domain_context: dict[str, str], *, api_key: str) -> Callable[[str], Awaitable[Position]]:
    """Real factory, matching the same closure-over-real-context pattern
    already established throughout `gate/orchestration.py` and
    `negotiation/subgraph.py`'s own `make_*_node` functions.

    A real, structural fact about `PositionCall`'s existing, already-
    tested type signature (`Callable[[str], Awaitable[Position]]`),
    confirmed by reading `negotiation/positions.py` before writing this
    file: the function receives ONLY a domain name, no other context --
    `generate_positions()` calls it once per conflicted domain via
    `asyncio.gather`, with nothing else in scope. For a real, live
    negotiation to say anything meaningfully domain-specific, the actual
    situational context (what's really happening in that domain right
    now) has to be closed over at construction time, not passed at call
    time -- exactly the same shape as `subgraph.py`'s own factories
    closing over `position_call`/`synthesis_call`/`effect_extractor`."""

    async def position_call(domain: str) -> Position:
        context = domain_context.get(domain, f"The {domain} domain is in conflict with at least one other domain.")
        prompt = (
            f"You are the {domain} domain's advocate in a real resource negotiation "
            "against one or more other domains. State your position based only on "
            f"the real situation described below -- never invent facts beyond it.\n\n"
            f"Real situation: {context}"
        )
        result = await _call_gemini_json(prompt, response_schema=_POSITION_SCHEMA, api_key=api_key)
        return Position(
            domain=domain,
            concern=result["concern"],
            severity_claim=result["severity_claim"],
            resource_claims=[],
            proposed_resolution=result["proposed_resolution"],
            evidence=[],
        )

    return position_call


def make_gemini_synthesis_call(*, api_key: str) -> Callable[[str], Awaitable[list[NegotiationOption]]]:
    """Real factory for `SynthesisCall`. The prompt itself is already
    fully built by `negotiation/synthesis.py`'s own real, tested
    `build_synthesis_prompt()` before this call is ever invoked, and
    already asks for "exactly two complete options, plus a 'do nothing'
    option" -- but this function only asks Gemini for the real, creative
    part (description, source_domains) of the two genuine options; the
    always-present "do nothing" option is appended afterward by code,
    never requested from the model. See `_DO_NOTHING_OPTION_ID`'s own
    comment for the real, live failure this avoids. `option_id`s for the
    two real options are also assigned deterministically here (`option_a`
    /`option_b`), not trusted to the model.

    Shape correctness beyond ID assignment (exactly 3 options total,
    source_domains grounded in real positions) is NOT re-checked here --
    `synthesize_options()`'s own real, already-tested `validate_
    synthesis_shape()` does that immediately after this call returns."""

    async def synthesis_call(prompt: str) -> list[NegotiationOption]:
        result = await _call_gemini_json(prompt, response_schema=_SYNTHESIS_SCHEMA, api_key=api_key)
        raw_options = result["options"]
        if len(raw_options) < 2:
            raise GeminiGenerationError(
                f"Gemini synthesis returned {len(raw_options)} real option(s), need at least 2"
            )
        # A second real, live-discovered gap: the prompt asks for
        # "exactly two," but a real, live response has been observed
        # returning 3 -- Gemini's structured-output mode doesn't
        # mechanically enforce array length from prose alone. Sliced to
        # the first 2 in code rather than trusted to prompt compliance,
        # the same "code decides structure" fix already applied to
        # option IDs above.
        real_option_ids = ["option_a", "option_b"]
        options = [
            NegotiationOption(
                option_id=real_option_ids[i],
                description=option["description"],
                source_domains=option["source_domains"],
            )
            for i, option in enumerate(raw_options[:2])
        ]
        options.append(NegotiationOption(option_id=_DO_NOTHING_OPTION_ID, description="Do nothing -- make no changes.", source_domains=[]))
        return options

    return synthesis_call
