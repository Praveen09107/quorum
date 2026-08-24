"""Real, live Gemini-backed translation from a chosen `NegotiationOption`'s
free-text `description` into the structured arguments one of the 5 real
domain agents' `build_*_proposal()` functions need -- the piece
`features/negotiation_choice.py`'s own top-of-file docstring named as
deliberately out of scope: "The queued job carries the real, already-
computed facts... for a future session's own real design work to turn
into real proposals -- not guessed at here." This module is that future
session (`DEC-127`).

ONLY THREE REAL DOMAINS ARE EVER POSSIBLE HERE, confirmed directly against
`gate/schemas.py` before designing this: `Position.domain: Literal
["calendar", "tasks", "finance"]` -- a negotiation can never involve
email or career, by the real, hardcoded schema's own type constraint. No
translation schema exists here for those two domains because a real
negotiation's `source_domains` can never legitimately name them.

A SINGLE CHOSEN OPTION CAN PRODUCE MULTIPLE REAL DOWNSTREAM ACTIONS, ONE
PER DOMAIN IN `source_domains` -- a real, deliberate reading of
`QUORUM_DATA_CONTRACTS.md` §5.6's own spec text ("downstream action*s*...
enqueued, *each* re-entering the Gate at its own stakes level"), confirmed
consistent with `negotiation/synthesis.py`'s real `validate_synthesis_
shape()`, which places no upper bound on `len(option.source_domains)` --
only that every listed domain must trace to a real `Position`. A real
option spanning two domains (e.g. "cut task scope AND push the deadline")
is not a hypothetical; `features/retry_queue_drainer.py` (this session's
other new module) processes each domain independently, translating and
re-entering the Gate separately for each.

`source_domains == []` (the real, always-present "do nothing" option,
per `gate/schemas.py`'s own `NegotiationOption` docstring) needs no real
translation at all -- handled entirely in `retry_queue_drainer.py`, never
reaching this module.

WHY EACH DOMAIN GETS THE MODEL ONLY THE STRUCTURED FIELDS ITS OWN REAL
`build_*_proposal()` NEEDS, NOT A FREE-FORM PAYLOAD: the same "the model
narrates, the code computes" discipline `negotiation/gemini_calls.py`
already established for `NegotiationOption`'s own `option_id`s -- Gemini
supplies the real, judgment-requiring content (an amount, a title, a
deadline), and this module's own code decides everything structural
(which agent function to call, `has_external_invitee=False` always for
calendar -- a real, disclosed, lower-stakes default described below,
never asked of the model).

`calendar`'s translated proposal is ALWAYS the lower-stakes
`CREATE_CALENDAR_EVENT_LOCAL` variant (`has_external_invitee=False`),
never `CREATE_CALENDAR_EVENT_EXTERNAL` -- a real, deliberate, disclosed
choice: a negotiation option's free text never names a real external
attendee's email address for this module to genuinely ground an
`EXTERNAL` proposal in, and guessing one would be a real fabrication this
project's whole Gate architecture exists to prevent. `tasks`'s translated
proposal is always `CREATE_TASK` (`existing_task_id=None`), never
`UPDATE_TASK`, for the identical real reason: a negotiation option's text
never names a real, existing task's UUID for this module to reference.

REAL MODEL, REUSED, NOT REDISCOVERED: `gemini-3.6-flash`, the same real,
already-live-confirmed model `negotiation/gemini_calls.py` (`DEC-121`)
and `gate/llm_calls.py` (`DEC-125`) already use for Gemini calls in this
backend -- no separate live discovery needed for a third use of a model
this backend has already twice confirmed live.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Awaitable, Callable

import httpx

DownstreamTranslationCall = Callable[[str, str], Awaitable[dict]]

GEMINI_TRANSLATION_MODEL = "gemini-3.6-flash"
_TRANSLATION_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_TRANSLATION_MODEL}:generateContent"


class DownstreamTranslationError(Exception):
    """Raised when a real translation call -- and every real retry of it
    -- fails, or asks for a domain this module has no real schema for.
    Never silently substituted with an invented proposal; the same
    "raise loud, never fabricate" principle every other real Gemini-
    backed call in this backend already follows."""


_FINANCE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "action": {"type": "STRING", "enum": ["log_expense", "update_budget"]},
        "amount": {"type": "NUMBER"},
        "category": {"type": "STRING"},
        "payee": {"type": "STRING", "nullable": True},
    },
    "required": ["action", "amount", "category", "payee"],
}

_TASKS_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "estimated_hours": {"type": "NUMBER"},
        "deadline_iso": {"type": "STRING", "nullable": True},
    },
    "required": ["title", "estimated_hours", "deadline_iso"],
}

_CALENDAR_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "start_iso": {"type": "STRING"},
        "end_iso": {"type": "STRING"},
    },
    "required": ["title", "start_iso", "end_iso"],
}

_SCHEMAS_BY_DOMAIN = {"finance": _FINANCE_SCHEMA, "tasks": _TASKS_SCHEMA, "calendar": _CALENDAR_SCHEMA}


def _build_translation_prompt(domain: str, description: str) -> str:
    now_iso = datetime.now(timezone.utc).isoformat()
    preamble = (
        "A user just chose a real option that resolves a real conflict "
        "between two or more of their own domains, in a negotiation this "
        "system already ran for them. Translate their chosen option's "
        "real description below into a structured action for the "
        f"{domain} domain specifically -- never invent a fact this "
        "description doesn't genuinely support.\n\n"
        f"Chosen option: {description}\n\n"
        f"Current real UTC time: {now_iso}\n\n"
    )
    if domain == "finance":
        return preamble + (
            "Decide: is this logging one new expense (log_expense) or "
            "changing a real budget ceiling itself (update_budget)? "
            "Extract a real, positive amount, a real category, and an "
            "optional payee (null if none is genuinely named)."
        )
    if domain == "tasks":
        return preamble + (
            "Extract a real title, a real, positive estimated_hours, "
            "and deadline_iso: a real ISO 8601 UTC datetime string if a "
            "real deadline is genuinely implied by the description, "
            "otherwise null -- never invent one that isn't there."
        )
    if domain == "calendar":
        return preamble + (
            "Extract a real title, start_iso and end_iso (real ISO 8601 "
            "UTC datetimes, end strictly after start). If no specific "
            "time is genuinely implied, propose one reasonable, real "
            "near-future working-hours slot rather than leaving either "
            "field unset."
        )
    raise DownstreamTranslationError(f"No real translation prompt for domain {domain!r}")


async def _call_gemini_json(prompt: str, *, response_schema: dict, api_key: str, max_retries: int = 2) -> dict:
    """Real, live call to Gemini's `generateContent`, structured JSON
    output, real retry on transient failure -- the same, now three-times-
    repeated local-helper pattern `negotiation/gemini_calls.py` and
    `gate/llm_calls.py` each already use for their own genuinely separate
    call sites, not forced into one shared abstraction across modules
    with different real callers and different real schemas."""
    last_error: Exception | None = None
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
        },
    }
    for _attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(_TRANSLATION_URL, headers={"x-goog-api-key": api_key}, json=body)
            if response.status_code != 200:
                last_error = DownstreamTranslationError(
                    f"Gemini generateContent returned {response.status_code}: {response.text[:500]}"
                )
                continue
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            last_error = exc
    raise DownstreamTranslationError(
        f"Gemini downstream-translation call failed after {max_retries} attempts: {last_error}"
    ) from last_error


def make_gemini_downstream_translation_call(*, api_key: str) -> DownstreamTranslationCall:
    """Real factory. The returned callable's real signature,
    `(domain, description) -> dict`, matches exactly what `features/
    retry_queue_drainer.py` needs to call per domain in a chosen option's
    real `source_domains`."""

    async def translation_call(domain: str, description: str) -> dict:
        schema = _SCHEMAS_BY_DOMAIN.get(domain)
        if schema is None:
            raise DownstreamTranslationError(
                f"No real translation schema for domain {domain!r} -- only "
                "'finance', 'tasks', 'calendar' are ever real, per "
                "Position.domain's own schema constraint."
            )
        prompt = _build_translation_prompt(domain, description)
        return await _call_gemini_json(prompt, response_schema=schema, api_key=api_key)

    return translation_call
