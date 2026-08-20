"""Real, live LLM-backed Stage B implementations for `gate/orchestration.py`'s
own injected `CriticCall`/`JudgeCall` types -- the first real implementation
of either, ever, in this backend. Confirmed by direct search before writing
this file: `CriticCall`/`JudgeCall` have existed as pure type signatures
since `IMPL_08`, with every real Gate test (`test_gate_orchestration.py`,
`self_test_harness.py`) exercising them only against hand-written fakes.
`self_test_harness.py`'s own fakes are deliberately left untouched by this
module -- its adversarial scenarios assert an exact expected decision per
scenario, which needs deterministic behavior to test the *orchestration*
logic, not a real model's judgment; that remains the right, separate
design, not something this module should collapse into.

MODEL ASSIGNMENT, per `QUORUM_GATE_SPECIFICATION.md` Sec 5.1 and CLAUDE.md's
own "must never be violated" architecture fact: the Critic runs on a
genuinely different model PROVIDER than the Judge -- Groq, not Gemini --
deliberate model diversity, not a cost optimization, never simplified onto
one provider.

REAL, DISCLOSED DEVIATION FROM THE SPEC'S NAMED CRITIC MODEL, confirmed
live before hardcoding anything, the same discipline `core/embeddings.py`
and `negotiation/gemini_calls.py` already established for their own model
choices: `QUORUM_GATE_SPECIFICATION.md` Sec 5.1 names "Groq-hosted Llama
3.3 70B" for the Critic. A real, live call to that exact model ID
(`llama-3.3-70b-versatile`) returned a real 404 (`model_not_found`)
against this project's own real Groq API key. A real, live
`GET /openai/v1/models` against the same key confirmed the full current
catalog has no Llama chat model left in it at any size -- only two tiny
(22M/86M) prompt-guard classifiers, unrelated audio models, and a handful
of other open-weight chat models. `openai/gpt-oss-120b` -- the largest
general-purpose chat model in that real, current catalog -- is used
instead: it preserves the actual, load-bearing property CLAUDE.md's rule
protects (a genuinely different provider AND a genuinely different model
family from Gemini), even though the specific historical model name is
gone from Groq's own catalog. Confirmed live and working, with a real
strict `json_schema` response format, before this module trusted it.
Logged as a real, disclosed deviation (`DEC-125`) -- never a silent
substitution.

A real, live-discovered behavior worth recording here because it directly
shaped this module's token-budget code: `openai/gpt-oss-120b` is a
reasoning model. A live call with a small `max_completion_tokens` budget
returned a real, empty `content` field with `finish_reason: "length"` --
every token was consumed by an internal `reasoning` field the model emits
before its real answer. This module budgets generously
(`_GROQ_MAX_COMPLETION_TOKENS`) and reads only `message.content`, never
`message.reasoning`, for the real structured answer.

THE JUDGE MODEL: `gemini-3.6-flash`, the same real model
`negotiation/gemini_calls.py` already discovered live and uses -- no
separate re-discovery needed here, same provider, same already-verified
model ID.

ANONYMIZATION, per `QUORUM_GATE_SPECIFICATION.md` Sec 5.3:
`gate/anonymization.py`'s real `randomize_objection_order()` runs here,
inside `make_gemini_judge_call()`, immediately before the Judge prompt is
built -- exactly the "calling code, before this function runs" the spec
names, deliberately kept out of `gate/prompts.py` itself and out of
`gate/orchestration.py`'s own already-tested state machine.

`revised_payload` IS AN ARBITRARY DICT, SHAPE UNKNOWN AHEAD OF TIME (it
must match whichever `ActionType`'s payload the proposal under review
actually has) -- Gemini's `responseSchema` needs concrete, enumerable
properties for an `OBJECT` type, so it cannot describe "any object"
directly. Asked for as a JSON-encoded STRING instead (`revised_payload_json`)
and `json.loads()`'d in code afterward, the same "code decides structure,
never trust the model with an open-ended schema" principle already
applied to `negotiation/gemini_calls.py`'s deterministic option IDs.
"""
from __future__ import annotations

import json
from typing import Awaitable, Callable

import httpx

from quorum_backend.gate.anonymization import randomize_objection_order
from quorum_backend.gate.prompts import build_critic_prompt, build_judge_prompt
from quorum_backend.gate.schemas import ActionProposal, Finding, GateVerdict, Objection

GROQ_CRITIC_MODEL = "openai/gpt-oss-120b"
_GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MAX_COMPLETION_TOKENS = 2048

GEMINI_JUDGE_MODEL = "gemini-3.6-flash"
_GEMINI_GENERATE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_JUDGE_MODEL}:generateContent"

# A real, code-assigned default -- never trusted to the model -- for the
# one case CLAUDE.md/self_test_harness.py's own precedent requires: a
# genuine "no real objections" Critic pass must still return exactly one
# signed-off Objection, never an empty list. Mirrors
# `self_test_harness.py::_critic_no_objection` exactly, so a real Critic
# pass and the fake used in adversarial scenarios agree on what "clean"
# looks like.
_NO_OBJECTIONS_FALLBACK = Objection(
    category="completeness",
    severity="low",
    description="Critic reviewed and found no real objections.",
    signed_off=True,
)


class GateLlmCallError(Exception):
    """Raised when a real Stage B provider call -- Groq or Gemini -- fails
    after every retry, or returns a shape this module cannot safely trust.
    Caught by `gate/orchestration.py`'s own `_call_with_retry` as an
    `InfrastructureFailure` trigger; never silently substituted with a
    fabricated verdict or objection list."""


_OBJECTIONS_RESPONSE_SCHEMA = {
    "name": "objections",
    "schema": {
        "type": "object",
        "properties": {
            "objections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": ["tone", "completeness", "safety", "commitment_wisdom", "factual"],
                        },
                        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                        "description": {"type": "string"},
                        "suggested_fix": {"type": ["string", "null"]},
                        "signed_off": {"type": "boolean"},
                    },
                    "required": ["category", "severity", "description", "suggested_fix", "signed_off"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["objections"],
        "additionalProperties": False,
    },
}

_JUDGE_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "decision": {"type": "STRING", "enum": ["approve", "revise", "reject", "escalate_to_human"]},
        "revised_payload_json": {"type": "STRING", "nullable": True},
    },
    "required": ["decision", "revised_payload_json"],
}


async def _call_groq_json(*, messages: list[dict], api_key: str, max_retries: int = 2) -> dict:
    """Real, live call to Groq's OpenAI-compatible `chat/completions`,
    strict `json_schema` structured output, with real retry on transient
    failure. Returns the already-parsed real JSON body from
    `message.content` -- never `message.reasoning`, which is real model
    scratch-work, not the structured answer."""
    last_error: Exception | None = None
    body = {
        "model": GROQ_CRITIC_MODEL,
        "messages": messages,
        "response_format": {"type": "json_schema", "json_schema": _OBJECTIONS_RESPONSE_SCHEMA},
        "max_completion_tokens": _GROQ_MAX_COMPLETION_TOKENS,
    }
    for _attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    _GROQ_CHAT_URL, headers={"Authorization": f"Bearer {api_key}"}, json=body
                )
            if response.status_code != 200:
                last_error = GateLlmCallError(f"Groq chat/completions returned {response.status_code}: {response.text[:500]}")
                continue
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            if not text:
                last_error = GateLlmCallError("Groq returned an empty message.content (reasoning-token budget likely exhausted)")
                continue
            return json.loads(text)
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            last_error = exc
    raise GateLlmCallError(f"Groq Critic call failed after {max_retries} attempts: {last_error}") from last_error


async def _call_gemini_json(*, prompt: str, api_key: str, max_retries: int = 2) -> dict:
    """Real, live call to Gemini's `generateContent`, structured JSON
    output, with real retry on transient failure. Mirrors
    `negotiation/gemini_calls.py`'s own local helper of the same name and
    shape -- a small, local duplicate rather than a forced shared import,
    the same reasoning that module's own docstring already gives for not
    collapsing genuinely separate call sites into one abstraction."""
    last_error: Exception | None = None
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": _JUDGE_RESPONSE_SCHEMA,
        },
    }
    for _attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(_GEMINI_GENERATE_URL, headers={"x-goog-api-key": api_key}, json=body)
            if response.status_code != 200:
                last_error = GateLlmCallError(f"Gemini generateContent returned {response.status_code}: {response.text[:500]}")
                continue
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            last_error = exc
    raise GateLlmCallError(f"Gemini Judge call failed after {max_retries} attempts: {last_error}") from last_error


def make_groq_critic_call(*, api_key: str) -> Callable[[ActionProposal, list[Finding]], Awaitable[list[Objection]]]:
    """Real factory matching `orchestration.py`'s own `CriticCall` type
    exactly (`Callable[[ActionProposal, list[Finding]], Awaitable[list[Objection]]]`)."""

    async def critic_call(proposal: ActionProposal, findings: list[Finding]) -> list[Objection]:
        prompt = build_critic_prompt(proposal, findings)
        result = await _call_groq_json(messages=[{"role": "user", "content": prompt}], api_key=api_key)
        raw_objections = result["objections"]
        if not raw_objections:
            # Never trust the model to remember the sentinel itself --
            # the same "code decides structure" principle already applied
            # to negotiation/gemini_calls.py's deterministic option IDs.
            return [_NO_OBJECTIONS_FALLBACK]
        return [
            Objection(
                category=o["category"],
                severity=o["severity"],
                description=o["description"],
                suggested_fix=o.get("suggested_fix"),
                signed_off=o["signed_off"],
            )
            for o in raw_objections
        ]

    return critic_call


def make_gemini_judge_call(
    *, api_key: str
) -> Callable[[ActionProposal, list[Finding], list[Objection]], Awaitable[GateVerdict]]:
    """Real factory matching `orchestration.py`'s own `JudgeCall` type
    exactly. Anonymizes `objections` (order-randomized, per
    `gate/anonymization.py`) before the prompt is ever built -- the real
    "calling code, before this function runs" step
    `QUORUM_GATE_SPECIFICATION.md` Sec 5.3 requires."""

    async def judge_call(proposal: ActionProposal, findings: list[Finding], objections: list[Objection]) -> GateVerdict:
        anonymized_objections = randomize_objection_order(objections)
        prompt = build_judge_prompt(proposal, findings, anonymized_objections)
        result = await _call_gemini_json(prompt=prompt, api_key=api_key)
        decision = result["decision"]
        revised_payload_json = result.get("revised_payload_json")

        revised_payload: dict | None = None
        if decision == "revise":
            # A real Judge decision of "revise" without a real revised
            # payload is a genuine Stage B contract violation -- never
            # silently treated as if the Judge meant "approve." Fails
            # loud via GateLlmCallError, which orchestration.py's own
            # _call_with_retry turns into a real InfrastructureFailure on
            # exhausted retries, never a fabricated verdict.
            if not revised_payload_json:
                raise GateLlmCallError("Gemini Judge returned decision='revise' with no real revised_payload_json")
            revised_payload = json.loads(revised_payload_json)

        return GateVerdict(
            decision=decision,
            revised_payload=revised_payload,
            findings=findings,
            objections=anonymized_objections,
            trace_id=str(proposal.proposal_id),
        )

    return judge_call
