"""The real, compiled negotiation subgraph -- the capstone that wires
IMPL_18 (trigger), IMPL_19 (positions + synthesis), and IMPL_20 (impact
simulation) into one continuous pipeline. HONEST DISCLOSURE:
construction-not-copy pattern, same as every negotiation/Gate file.

No new arithmetic or business logic lives here -- every real computation
was already built and tested across the three prior sessions. This
session's entire job is correct sequencing and correct routing: scan ->
(conditionally) generate_positions -> synthesize -> simulate_impact.

Confirmed before writing this, not assumed: IMPL_19's position and
synthesis calls are genuinely async (real asyncio.gather). A standalone
proof-of-concept confirmed LangGraph requires .ainvoke(), not .invoke(),
for a graph containing real async nodes -- the same discipline applied to
every prior LangGraph API decision in this project (career_agent.py's
conditional edges included).
"""
from __future__ import annotations

from typing import Callable, TypedDict

from langgraph.graph import END, StateGraph

from quorum_backend.gate.schemas import NegotiationOption, Position, ResourceClaim, ImpactDelta
from quorum_backend.negotiation.impact_simulator import DomainSnapshot, OptionEffect, simulate_all_options
from quorum_backend.negotiation.positions import PositionCall, generate_positions
from quorum_backend.negotiation.synthesis import SynthesisCall, synthesize_options
from quorum_backend.negotiation.trigger import DomainState, scan_for_conflicts

# Turning a synthesized option's natural-language description into a real
# OptionEffect is genuine domain-specific interpretation -- out of scope
# for this session, injected here exactly like every other real/external
# boundary in this project (llm_call, position_call, synthesis_call).
EffectExtractor = Callable[[NegotiationOption], OptionEffect]


class NegotiationState(TypedDict):
    resource_claims: list[ResourceClaim]
    domain_states: dict[str, DomainState]
    baseline: DomainSnapshot
    conflicted_domains: list[str] | None
    triggers_negotiation: bool | None
    positions: list[Position] | None
    options: list[NegotiationOption] | None
    impact: dict[str, list[ImpactDelta]] | None


def make_scan_node():
    def scan_node(state: NegotiationState) -> dict:
        result = scan_for_conflicts(state["resource_claims"], state["domain_states"])
        return {
            "conflicted_domains": result.conflicted_domains,
            "triggers_negotiation": result.triggers_negotiation,
        }

    return scan_node


def route_after_scan(state: NegotiationState) -> str:
    """Real conditional routing: proceeds to position generation only when
    scan_for_conflicts genuinely found 2+ conflicted domains. A non-
    conflict short-circuits here, before any LLM call is ever made."""

    if state.get("triggers_negotiation"):
        return "generate_positions"
    return END


def make_generate_positions_node(position_call: PositionCall):
    """Factory -- position_call is injected, never imported or called by
    name directly, same discipline as every other real/external boundary
    in this project."""

    async def generate_positions_node(state: NegotiationState) -> dict:
        positions = await generate_positions(state["conflicted_domains"] or [], position_call)
        return {"positions": positions}

    return generate_positions_node


def make_synthesize_node(synthesis_call: SynthesisCall):
    async def synthesize_node(state: NegotiationState) -> dict:
        options = await synthesize_options(state["positions"] or [], synthesis_call)
        return {"options": options}

    return synthesize_node


def make_simulate_impact_node(effect_extractor: EffectExtractor):
    """Real arithmetic (simulate_all_options) was already built and proven
    correct in IMPL_20 -- this node's only job is turning each real,
    synthesized option into the OptionEffect that arithmetic needs, via the
    injected effect_extractor, then handing the same baseline to every
    option so none corrupts another's computation."""

    def simulate_impact_node(state: NegotiationState) -> dict:
        option_effects = {
            option.option_id: effect_extractor(option) for option in (state["options"] or [])
        }
        impact = simulate_all_options(state["baseline"], option_effects)
        return {"impact": impact}

    return simulate_impact_node


def build_negotiation_graph(
    position_call: PositionCall,
    synthesis_call: SynthesisCall,
    effect_extractor: EffectExtractor,
):
    graph = StateGraph(NegotiationState)
    graph.add_node("scan", make_scan_node())
    graph.add_node("generate_positions", make_generate_positions_node(position_call))
    graph.add_node("synthesize", make_synthesize_node(synthesis_call))
    graph.add_node("simulate_impact", make_simulate_impact_node(effect_extractor))

    graph.set_entry_point("scan")
    graph.add_conditional_edges(
        "scan", route_after_scan, {"generate_positions": "generate_positions", END: END}
    )
    graph.add_edge("generate_positions", "synthesize")
    graph.add_edge("synthesize", "simulate_impact")
    graph.add_edge("simulate_impact", END)

    return graph.compile()
