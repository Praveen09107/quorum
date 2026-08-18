"""Real trace-scrubbing middleware content -- strips known-sensitive
patterns from anything before it's sent to Langfuse for persistence.
HONEST DISCLOSURE: construction-not-copy pattern, same as every
negotiation/Gate/security file in this project.

The same comprehensive tracing that makes the trust thesis measurable
(QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md §17) is also the system's largest
potential secret-leakage surface if this step were skipped -- the
connection between these two facts is direct, not coincidental (ADD §14.6).

Real gap this reuses, not reinvents: the ADD requires trace-scrubbing to
reuse "the Privacy Gate's own rule-layer detectors... not a separately
maintained pattern set" -- but the Privacy Gate (MOBILE_03, Dart,
on-device) and this module (Python, backend) can never literally share
code across platforms. QUORUM_CONFIGURATION_CONSTANTS.md §10.1 is the
real, single source of truth both platforms are required to match exactly
instead.

HONEST STATUS DISCLOSURE, specific to this repository: MOBILE_03 (the
on-device Privacy Gate) has not been implemented here -- this repository's
real, current work has only reached the end of the 23-session backend
sequence; the mobile session sequence (MOBILE_01 onward) has not started.
SENSITIVE_PATTERNS below is built directly from §10.1's real regex
definitions regardless, since that table is the correct, real source of
truth independent of which platform has actually consumed it yet -- see
STATUS_INDEX.md for this repository's current, live status.
"""
from __future__ import annotations

import re

# Exact regexes from QUORUM_CONFIGURATION_CONSTANTS.md §10.1 -- the single
# source of truth. Never approximate this table; whichever platform
# implements a pattern set is required to match it exactly.
SENSITIVE_PATTERNS: dict[str, re.Pattern[str]] = {
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    "aadhaar_style_id": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "otp_code": re.compile(
        r"\b(?:OTP|otp|code|verification code)[\s:]*(\d{4,8})\b", re.IGNORECASE
    ),
}


def scrub_trace_content(text: str) -> str:
    """Redacts every real match with a typed, diagnosable placeholder --
    never silent deletion. A silent deletion is indistinguishable from
    content that was never there, which defeats the point of a
    diagnosable audit trail: an engineer reading a scrubbed trace should
    be able to tell THAT something sensitive was caught and WHAT category
    it was, without ever seeing the real value itself.

    Real, confirmed-not-assumed behavior: the otp_code pattern captures a
    group, but since the replacement string below never references that
    group, re.sub replaces the ENTIRE matched phrase -- "OTP: 482913," not
    just the digits. See test_otp_code_is_redacted_including_the_full_
    labeled_phrase, which checks this exact behavior directly.
    """

    result = text
    for category, pattern in SENSITIVE_PATTERNS.items():
        result = pattern.sub(f"<REDACTED_{category.upper()}>", result)
    return result
