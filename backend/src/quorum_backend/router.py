"""The Router — stakes lookup + complexity classification.

HONEST DISCLOSURE: IMPL_09_ROUTER.md describes this file's real, tested
properties in prose but never reproduces its literal source. This is a
real, careful construction from that description and from
QUORUM_CONFIGURATION_CONSTANTS.md Sec 1's exact, verbatim stakes table --
not a copy of given code.

Stakes is a hardcoded, closed-enum lookup by ActionType -- never learned,
never inferred from model confidence. A safety boundary must be auditable
by inspection. Adding a new ActionType requires a corresponding stakes-
table row in the same change -- there is no default; an unmapped action
type is a bug, caught loudly by get_stakes(), never silently defaulted.

Complexity is computed from structural features, never self-assessed model
confidence -- see ComplexitySignals below, which deliberately has no
confidence field anywhere.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from quorum_backend.gate.schemas import ActionType, Stakes

STAKES_TABLE: dict[ActionType, Stakes] = {
    ActionType.SEND_EMAIL: Stakes.S3,
    ActionType.CREATE_CALENDAR_EVENT_EXTERNAL: Stakes.S3,
    ActionType.CREATE_CALENDAR_EVENT_LOCAL: Stakes.S2,
    ActionType.CREATE_TASK: Stakes.S1,
    ActionType.UPDATE_TASK: Stakes.S1,
    ActionType.LOG_EXPENSE: Stakes.S1,
    ActionType.UPDATE_BUDGET: Stakes.S2,
    ActionType.CREATE_NOTE: Stakes.S1,
    ActionType.UPDATE_APPLICATION_STATUS: Stakes.S1,
    ActionType.ARCHIVE_EMAIL: Stakes.S1,
    ActionType.LABEL_EMAIL: Stakes.S0,
}


def get_stakes(action_type: ActionType) -> Stakes:
    """Raises loudly on an unmapped type -- never silently defaults. An
    action type with no stakes-table entry is a real bug, per
    QUORUM_CONFIGURATION_CONSTANTS.md Sec 1's own stated rule."""
    try:
        return STAKES_TABLE[action_type]
    except KeyError as exc:
        raise ValueError(
            f"No stakes-table entry for action type {action_type!r} -- "
            "every real ActionType requires an explicit row, no default exists."
        ) from exc


class Complexity(str, Enum):
    C0 = "C0"  # on-device eligible
    C1 = "C1"  # cloud, single-domain
    C2 = "C2"  # cloud, multi-domain / negotiation


class ComplexitySignals(BaseModel):
    """Structural features only -- deliberately no confidence field
    anywhere. Self-assessed model confidence as a routing signal is
    rejected permanently per this project's own design history: small
    models produce confident-sounding text regardless of correctness."""

    domain_count: int
    requires_cross_reference: bool
    is_ambiguous: bool
    text_length: int


def compute_complexity(signals: ComplexitySignals) -> Complexity:
    """Cold-start rule thresholds -- upgrades to a trained classical-ML
    classifier only once real replay data exists (not yet, and not in this
    repository's current scope).

    Real, exact branches, in order:
      1. domain_count >= 2 -> C2, always, regardless of any other signal.
      2. is_ambiguous OR requires_cross_reference (domain_count < 2) -> C1.
      3. text_length > 280, with none of the above true -> C1, a
         deliberately conservative default, not C0.
      4. Otherwise -> C0.
    """
    if signals.domain_count >= 2:
        return Complexity.C2
    if signals.is_ambiguous or signals.requires_cross_reference:
        return Complexity.C1
    if signals.text_length > 280:
        return Complexity.C1
    return Complexity.C0
