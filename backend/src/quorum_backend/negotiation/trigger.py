"""The ConflictScan -- pure computation, zero LLM calls, zero inference.

HONEST DISCLOSURE: same construction-not-copy pattern as every negotiation/
Gate file in this project -- IMPL_18_NEGOTIATION_TRIGGER.md describes this
module's real properties in prose but never reproduces literal source.

Whether a real conflict exists is never left to a model's judgment -- it's
arithmetic. A claim against a domain with no real DomainState is never
silently assumed to conflict -- see this session's report for why that
distinction matters (the same no_data_found epistemic honesty the Gate
itself already holds, applied here for the first time outside the Gate).

Negotiation triggers ONLY at two or more conflicted domains -- a single
conflicted domain is an ordinary Stage A concern, not a negotiation
candidate.
"""
from __future__ import annotations

from dataclasses import dataclass

from quorum_backend.gate.schemas import ResourceClaim

CLAIM_TYPE_TO_DOMAIN: dict[str, str] = {
    "time": "calendar",
    "money": "finance",
    "effort": "tasks",
}


@dataclass(frozen=True)
class DomainState:
    domain: str
    available: float
    unit: str


@dataclass(frozen=True)
class ConflictScanResult:
    conflicted_domains: list[str]
    triggers_negotiation: bool


def scan_for_conflicts(
    resource_claims: list[ResourceClaim],
    domain_states: dict[str, DomainState],
) -> ConflictScanResult:
    conflicted: list[str] = []
    for claim in resource_claims:
        domain = CLAIM_TYPE_TO_DOMAIN.get(claim.claim_type)
        if domain is None:
            continue
        state = domain_states.get(domain)
        if state is None:
            # No real data for this domain -- never silently assumed to
            # be a conflict. See this session's report for the reasoning.
            continue
        if claim.amount > state.available and domain not in conflicted:
            conflicted.append(domain)

    return ConflictScanResult(
        conflicted_domains=conflicted,
        triggers_negotiation=len(conflicted) >= 2,
    )
