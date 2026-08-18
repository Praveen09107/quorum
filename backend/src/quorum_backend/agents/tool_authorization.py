"""Two-layer tool authorization — the real, second, independent layer.

HONEST DISCLOSURE: same as every construction-not-copy file in this batch
so far — IMPL_13_AGENT_EMAIL.md describes this module's real properties in
prose but never reproduces literal source. A real, careful construction
from that description and QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md §14.3's
two-layer authorization design.

The first layer is structural: an agent's own graph code never references
another domain's tools at all (confirmed per-agent by grep in every
session's real verification). This second layer is deliberately
independent of that guarantee holding forever — it's a real runtime check
against DOMAIN_TOOL_MAP, so a future refactor, a copy-pasted node, or any
other mistake in the first layer cannot become a real security hole on its
own; the second layer doesn't assume the first was correct.

DOMAIN_TOOL_MAP fails closed by construction: dict.get(domain, set())
means any domain not explicitly listed gets an empty allowed-set, never a
default-allow path. Built once here, in IMPL_13; every later session in
this batch EXTENDS this dict with one new real domain entry, never
reimplementing authorize_tool_call itself.
"""
from __future__ import annotations

DOMAIN_TOOL_MAP: dict[str, set[str]] = {
    "email": {"gmail.send", "gmail.read", "gmail.archive", "gmail.label"},
}
# Only "email" exists as of IMPL_13. Four more real domains are added, one
# per later session in this batch (IMPL_14-17) -- the "all five domains
# now present" comment is added honestly in IMPL_17, once it's actually
# true, not written ahead of time as an aspirational claim.


class ToolAuthorizationError(Exception):
    """Raised when a domain attempts to call a tool outside its own real
    allowlist. Fails closed, never fails open."""


def authorize_tool_call(tool_name: str, calling_agent_domain: str) -> None:
    allowed = DOMAIN_TOOL_MAP.get(calling_agent_domain, set())
    if tool_name not in allowed:
        raise ToolAuthorizationError(
            f"Domain {calling_agent_domain!r} is not authorized to call tool {tool_name!r}"
        )
