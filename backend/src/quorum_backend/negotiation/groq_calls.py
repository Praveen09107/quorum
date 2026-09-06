"""Real, live Groq-backed `PositionCall`/`SynthesisCall` implementations
-- the first real Stage-B-style LLM content-generation call this backend
has ever made. `core/embeddings.py` (Roadmap Phase 4a) was the first real
outbound Gemini call of any kind; this module was originally that same
Gemini-backed generation call for negotiation content (`DEC-121`, as
`negotiation/gemini_calls.py`) -- see "REAL, DISCLOSED MIGRATION FROM
GEMINI" below for why it now calls Groq instead, and the real, first
implementation of the negotiation subgraph's own injected
`PositionCall`/`SynthesisCall` types (`negotiation/positions.py`,
`negotiation/synthesis.py`) -- both have existed since `IMPL_18`/`IMPL_19`
as pure type signatures.

REAL, DISCLOSED MIGRATION FROM GEMINI, `DEC-166`: this module's real
`generateContent` calls (originally `gemini-3.6-flash`, confirmed live in
`DEC-121`) shared one real, hard 20-request/day free-tier quota
(`core/gemini_quota.py`, `DEC-165`) with five other real call sites across
this backend -- `gate/llm_calls.py`'s own Judge, `features/quick_capture.py`,
`negotiation/downstream_translation.py`, `features/career_digest.py`, and
this module. `QUORUM_FINAL_COMPLETION_PLAN.md` Session 1 rebalances that
real, shared pressure: every real `generateContent` call site EXCEPT the
Judge (`gate/llm_calls.py::make_gemini_judge_call`, kept on Gemini
deliberately -- CLAUDE.md's own "must never be violated" architecture fact
requires the Critic and Judge to run on genuinely different model
PROVIDERS, and the Critic is already Groq) moves to Groq instead, which
this backend's own real, live-confirmed Critic usage (`gate/llm_calls.py`,
`DEC-125`) already has meaningfully higher real headroom on. `GEMINI_
GENERATION_MODEL`/`_call_gemini_json`/`GeminiGenerationError` are gone from
this file; `GROQ_GENERATION_MODEL`/`_call_groq_json`/`GroqGenerationError`
replace them, and this module no longer reserves any `core/gemini_
quota.py` slot at all -- there is nothing left here for that guard to
protect.

MODEL, reused rather than rediscovered: `openai/gpt-oss-120b`, the exact
real, live-confirmed model `gate/llm_calls.py::GROQ_CRITIC_MODEL` already
uses (`DEC-125`'s own real, disclosed deviation from the spec's named
Critic model, `llama-3.3-70b-versatile`, which returned a real 404 against
this project's real Groq catalog) -- no separate live discovery needed for
a second real Groq use of the same already-verified model.

STRUCTURED OUTPUT, not free-text-then-regex-parse: Groq's OpenAI-compatible
`response_format: {"type": "json_schema", ...}`, the same real, strict,
already-live-confirmed shape `gate/llm_calls.py::_call_groq_json` uses --
NOT a verbatim copy of that function (it is hardcoded to one schema, the
Critic's own `_OBJECTIONS_RESPONSE_SCHEMA`), but the same real HTTP
mechanics, generalized here to accept whichever of this module's own two
real schemas (`_POSITION_SCHEMA`, `_SYNTHESIS_SCHEMA`) a given real call
needs. A REAL, LIVE-VERIFIED SCHEMA-SHAPE DIFFERENCE, confirmed directly
rather than assumed to generalize from the Gemini version: Gemini's
`responseSchema` uses UPPERCASE JSON-schema type strings (`"OBJECT"`,
`"STRING"`, `"ARRAY"`); Groq's `json_schema` requires standard LOWERCASE
types (`"object"`, `"string"`, `"array"`) plus a `{"name", "schema"}`
wrapper with `"additionalProperties": false` -- both real schemas below
were rewritten to that shape, never copy-pasted from the Gemini version.

RETRY DISCIPLINE, deliberately separate from `gate/orchestration.py`'s
own `_call_with_retry`: that function is typed specifically for Stage B's
`CriticCall`/`JudgeCall` shape (`Awaitable[GateVerdict]`); this module's
two call types return different real shapes (`Position`, `list[
NegotiationOption]`), so a small, local retry helper is used instead of
forcing an artificial shared abstraction across two genuinely different
call signatures -- the same real principle `gate/llm_calls.py::
_call_groq_json` and `_call_gemini_json` already apply to each other.
No artificial inter-attempt sleep: matching `gate/llm_calls.py::
_call_groq_json`'s own real, already-live Groq retry loop, which has
never needed one -- Groq's own real, observed failure modes at this
call volume have not shown the same per-minute rate-limit backoff
Gemini's real `429` responses explicitly asked for (the reason the
superseded Gemini version of this module slept between retries). Same
real principle both places: a transient provider failure retries; every
attempt failing raises loud, never fabricates a plausible-looking result.
"""
from __future__ import annotations

import json
from typing import Awaitable, Callable

import httpx

from quorum_backend.gate.schemas import NegotiationOption, Position

GROQ_GENERATION_MODEL = "openai/gpt-oss-120b"

_GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MAX_COMPLETION_TOKENS = 2048


class GroqGenerationError(Exception):
    """Raised when a real Groq chat/completions call -- and every real
    retry of it -- fails. Never silently substituted with an invented
    Position/NegotiationOption, which would be the exact "model
    fabricates, code doesn't verify" failure this project's whole Gate
    architecture exists to prevent."""


async def _call_groq_json(prompt: str, *, response_schema: dict, api_key: str, max_retries: int = 2) -> dict:
    """Real, live call to Groq's OpenAI-compatible `chat/completions`,
    strict `json_schema` structured output, with real retry on transient
    failure. Returns the already-parsed real JSON body from
    `message.content` -- never `message.reasoning`, which is real model
    scratch-work `gate/llm_calls.py`'s own top-of-file docstring already
    disclosed `openai/gpt-oss-120b`'s real, live-observed reasoning-model
    behavior for; callers validate/construct real Pydantic objects from
    the returned dict, never trust it blindly.

    `response_schema` is the full real Groq `json_schema` wrapper
    (`{"name": ..., "schema": {...}}`), not a bare JSON Schema object --
    matching exactly what `response_format.json_schema` needs."""
    last_error: Exception | None = None
    body = {
        "model": GROQ_GENERATION_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_schema", "json_schema": response_schema},
        "max_completion_tokens": _GROQ_MAX_COMPLETION_TOKENS,
    }
    for _attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(_GROQ_CHAT_URL, headers={"Authorization": f"Bearer {api_key}"}, json=body)
            if response.status_code != 200:
                last_error = GroqGenerationError(f"Groq chat/completions returned {response.status_code}: {response.text[:500]}")
                continue
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            if not text:
                last_error = GroqGenerationError("Groq returned an empty message.content (reasoning-token budget likely exhausted)")
                continue
            return json.loads(text)
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            last_error = exc
    raise GroqGenerationError(f"Groq generation call failed after {max_retries} attempts: {last_error}") from last_error


_POSITION_SCHEMA = {
    "name": "position",
    "schema": {
        "type": "object",
        "properties": {
            "concern": {"type": "string"},
            "severity_claim": {"type": "string"},
            "proposed_resolution": {"type": "string"},
        },
        "required": ["concern", "severity_claim", "proposed_resolution"],
        "additionalProperties": False,
    },
}

_SYNTHESIS_SCHEMA = {
    "name": "synthesis",
    "schema": {
        "type": "object",
        "properties": {
            "options": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "source_domains": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["description", "source_domains"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["options"],
        "additionalProperties": False,
    },
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
# just arithmetic. Still true under Groq: never re-asked of the model.
_DO_NOTHING_OPTION_ID = "do_nothing"


def make_groq_position_call(domain_context: dict[str, str], *, api_key: str) -> Callable[[str], Awaitable[Position]]:
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
        result = await _call_groq_json(prompt, response_schema=_POSITION_SCHEMA, api_key=api_key)
        return Position(
            domain=domain,
            concern=result["concern"],
            severity_claim=result["severity_claim"],
            resource_claims=[],
            proposed_resolution=result["proposed_resolution"],
            evidence=[],
        )

    return position_call


def make_groq_synthesis_call(*, api_key: str) -> Callable[[str], Awaitable[list[NegotiationOption]]]:
    """Real factory for `SynthesisCall`. The prompt itself is already
    fully built by `negotiation/synthesis.py`'s own real, tested
    `build_synthesis_prompt()` before this call is ever invoked, and
    already asks for "exactly two complete options, plus a 'do nothing'
    option" -- but this function only asks the model for the real,
    creative part (description, source_domains) of the two genuine
    options; the always-present "do nothing" option is appended
    afterward by code, never requested from the model. See
    `_DO_NOTHING_OPTION_ID`'s own comment for the real, live failure
    this avoids. `option_id`s for the two real options are also assigned
    deterministically here (`option_a`/`option_b`), not trusted to the
    model.

    Shape correctness beyond ID assignment (exactly 3 options total,
    source_domains grounded in real positions) is NOT re-checked here --
    `synthesize_options()`'s own real, already-tested `validate_
    synthesis_shape()` does that immediately after this call returns."""

    async def synthesis_call(prompt: str) -> list[NegotiationOption]:
        result = await _call_groq_json(prompt, response_schema=_SYNTHESIS_SCHEMA, api_key=api_key)
        raw_options = result["options"]
        if len(raw_options) < 2:
            raise GroqGenerationError(
                f"Groq synthesis returned {len(raw_options)} real option(s), need at least 2"
            )
        # A real, live-discovered gap under the original Gemini version of
        # this module: the prompt asks for "exactly two," but a real,
        # live response was observed returning 3 -- structured-output
        # mode doesn't mechanically enforce array length from prose
        # alone. Sliced to the first 2 in code rather than trusted to
        # prompt compliance, the same "code decides structure" fix
        # already applied to option IDs above; kept under Groq as a
        # defensive real safeguard even though it hasn't yet been
        # observed live on this provider.
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
