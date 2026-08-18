"""Real parallel Position generation. HONEST DISCLOSURE: construction-not-
copy pattern, same as every negotiation/Gate file.

One parallel call per conflicted domain -- uninvolved domains stay
completely silent, zero wasted calls, zero added latency since real calls
are independent.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from quorum_backend.gate.schemas import Position

PositionCall = Callable[[str], Awaitable[Position]]


async def generate_positions(
    conflicted_domains: list[str],
    position_call: PositionCall,
) -> list[Position]:
    results = await asyncio.gather(*(position_call(domain) for domain in conflicted_domains))
    return list(results)
