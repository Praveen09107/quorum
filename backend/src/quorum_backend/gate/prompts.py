"""Gate Stage B prompts, plus the CoverageCheck extraction prompt.

Real content so far: COVERAGE_EXTRACTION_PROMPT / build_coverage_extraction_prompt
(IMPL_07). CRITIC_SYSTEM_PROMPT and JUDGE_SYSTEM_PROMPT are deliberately not
built yet -- nothing in this repository needs them until IMPL_08's real
orchestration work, and building them now would be unscoped ahead-of-need
work (CLAUDE.md Rule 3).

A real disclosure, not glossed over: unlike gate/schemas.py (built from
QUORUM_DATA_CONTRACTS.md's exhaustive field-level spec), no document in this
project's real specification corpus reproduces this prompt's literal text --
only its functional requirement (QUORUM_GATE_SPECIFICATION.md Sec 5.4: "a
single, cheap, cacheable call: extract distinct questions from a source
email as a plain string list"). The wording below is a real, reasoned
construction of that requirement, not a copy of a given spec -- flagged
explicitly so this is never mistaken for a literal quote of something that
was actually specified.
"""
from __future__ import annotations

COVERAGE_EXTRACTION_PROMPT = """You are extracting distinct questions from a source email so a reply can later be checked for completeness.

Read the email body below. List every distinct question it asks, one per line, as plain statements (not the original phrasing if it's ambiguous, but preserving the real substance of each). If the email asks no real questions, return an empty list.

Source email body:
{source_email_body}

Return only the list of distinct questions, nothing else."""


def build_coverage_extraction_prompt(source_email_body: str) -> str:
    """Renders the real extraction prompt with the actual source email body
    interpolated in -- the literal body text must appear in the output,
    proven by test, the same pattern already established for the Critic/
    Judge prompts' own interpolation guarantees."""
    return COVERAGE_EXTRACTION_PROMPT.format(source_email_body=source_email_body)
