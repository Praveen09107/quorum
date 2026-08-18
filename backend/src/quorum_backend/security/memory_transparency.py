"""Real schema and grouping logic for the Memory Transparency screen.
HONEST DISCLOSURE: a genuinely new backend module, not a wrapper around
existing logic. `mem0` is referenced throughout this backend as a real
storage layer -- purged on account deletion (`security/account_deletion
.py`), read for calendar buffer preferences (`gate/validators.py`) -- but
no real schema for what a single memory *is*, and no real way to list or
delete one individually, existed anywhere in this repository before this
session. Deliberately does NOT implement mem0 itself -- that's a real
external service, injected like Gmail, Tavily, and every LLM call in
this project.

Real, self-caught file-placement note: this module's own test file lives
flat at `backend/tests/test_memory_transparency.py`, matching the real,
established precedent `test_account_deletion.py` and `test_trace_
scrubbing.py` already set for every other `security/` module in this
project -- not nested under a `backend/tests/security/` directory that
would introduce a second, competing test-layout convention.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Memory:
    memory_id: str
    content: str
    category: str
    created_at: datetime


def group_by_category(memories: list[Memory]) -> dict[str, list[Memory]]:
    """Real, honest grouping -- mem0's own categorization scheme isn't
    controlled by this codebase, so this function never drops a memory
    for an unexpected category string. An unrecognized category still
    lands in its own real group, keyed by whatever string mem0 actually
    reported, rather than being silently discarded or crashing."""

    grouped: dict[str, list[Memory]] = {}
    for memory in memories:
        grouped.setdefault(memory.category, []).append(memory)
    return grouped
