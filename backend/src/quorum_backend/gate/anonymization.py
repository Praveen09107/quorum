"""Real orchestration-layer anonymization for Gate Stage B's Judge call --
per QUORUM_GATE_SPECIFICATION.md Sec 5.3: "anonymization is an
orchestration-layer responsibility, not a prompt-layer one... role-
stripping and objection-order-randomization happen in the calling code
*before* [the Judge prompt] runs, so that discipline can be independently
unit-tested rather than trusted to prompt phrasing alone."

Role-stripping in practice: `gate/schemas.py`'s real `Objection` has no
identity/author field to begin with, confirmed by direct reading before
writing this module -- there is no persona for a Critic instance to leak
through the schema itself, so there is nothing for code to strip out of
the data. What this module does concretely, and what is real and
testable, is the other named half: a genuine, code-level randomization of
objection order, so a real, multi-objection Judge prompt never carries a
consistent primacy/recency signal from argument order alone, matching
QUORUM_GATE_SPECIFICATION.md Sec 2's "role-stripped, order-randomized"
description of the real Judge call.
"""
from __future__ import annotations

import random

from quorum_backend.gate.schemas import Objection


def randomize_objection_order(
    objections: list[Objection], rng: random.Random | None = None
) -> list[Objection]:
    """Returns a real, shuffled COPY -- never mutates the caller's list.
    Accepts an optional seeded `random.Random` so tests can assert a real,
    deterministic shuffle rather than relying on statistical odds across
    repeated runs."""
    shuffled = list(objections)
    (rng or random).shuffle(shuffled)
    return shuffled
