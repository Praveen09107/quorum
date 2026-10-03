"""Real, live task-completion/cancellation -- closes a real, previously-
undiscovered gap found during this session's live on-device redesign
audit: `tasks.status` has a real, closed three-value set (`open`/`done`/
`cancelled`, a database `CHECK` constraint, per `CLAUDE.md`), but no
real code path anywhere in this backend's entire history has ever
written anything other than the hardcoded `'open'` a real `CREATE_TASK`
insert uses. `UPDATE_TASK` (`action_executor.py`) only ever touches
`title`/`estimated_hours`/`deadline` -- confirmed directly by reading
its own real SQL before writing this module, not assumed. A real task
could be created; a real task's status could never actually change.

Mirrors `features/action_approval.py`'s own real design exactly, for
the same real reason: this is a direct, deterministic state change a
signed-in user triggers by tapping something in the real UI, not a new
natural-language proposal that needs a real Gate review -- the same
"a direct UI action skips the Gate; the human IS the already-understood
decision" precedent that module's own routes established. Never routed
through `quick_capture`/the Gate/an LLM call -- CLAUDE.md's own drift
pattern #1 ("reaching for an LLM call to check something checkable in
code") applies here just as much as it does to Stage A: whether a task
exists and is still open is a plain database fact, not a judgment call.

Deliberately real, narrow transitions only: `open -> done` and
`open -> cancelled`. Both are real, closed, one-way terminal
transitions -- there is no real "reopen a done/cancelled task" affordance
anywhere in this app, and this module does not invent one. Attempting
either transition on a task that is not currently `open` (already done,
already cancelled, or real per-user ownership doesn't match) is treated
as the same honest, real "nothing to do here" outcome as `action_
approval.py`'s own `PendingActionNotApprovable`."""
from __future__ import annotations

import uuid

import asyncpg


class TaskNotFound(Exception):
    """No real `tasks` row with this `task_id` exists for this exact
    user -- deliberately indistinguishable from "exists but belongs to
    someone else," the same "never confirm another user's data exists"
    discipline `features/action_approval.py` already established."""


class TaskNotUpdatable(Exception):
    """A real row was found, but it is not currently `open` -- already
    `done`, already `cancelled`. Both are real, closed terminal states;
    neither this module nor any other real code path in this backend
    ever transitions a task back out of one."""


async def _transition(pool: asyncpg.Pool, *, user_id: str, task_id: str, new_status: str) -> None:
    async with pool.acquire() as conn:
        # A single, real, conditional `UPDATE ... WHERE status = 'open'`
        # is both the existence check and the write -- there is no
        # separate real SELECT to race against (unlike `action_approval.
        # py`'s own multi-step approve flow, which genuinely needs a
        # held lock across a real external HTTP call this one never
        # makes). Two real concurrent taps on the same task can only
        # ever produce one real `UPDATE 1`; the second honestly reports
        # `TaskNotUpdatable`, never a second real transition.
        status = await conn.execute(
            "UPDATE tasks SET status = $3 WHERE task_id = $1 AND user_id = $2 AND status = 'open'",
            uuid.UUID(task_id),
            uuid.UUID(user_id),
            new_status,
        )
        if status == "UPDATE 1":
            return
        exists = await conn.fetchval(
            "SELECT 1 FROM tasks WHERE task_id = $1 AND user_id = $2",
            uuid.UUID(task_id),
            uuid.UUID(user_id),
        )
        if exists is None:
            raise TaskNotFound(f"No real tasks row {task_id!r} exists for this user.")
        raise TaskNotUpdatable("This task is no longer open -- it has already been completed or cancelled.")


async def complete_task(pool: asyncpg.Pool, *, user_id: str, task_id: str) -> None:
    """The one real way a `tasks` row's status has ever become `'done'`
    anywhere in this backend's history."""
    await _transition(pool, user_id=user_id, task_id=task_id, new_status="done")


async def cancel_task(pool: asyncpg.Pool, *, user_id: str, task_id: str) -> None:
    """The one real way a `tasks` row's status has ever become
    `'cancelled'` anywhere in this backend's history."""
    await _transition(pool, user_id=user_id, task_id=task_id, new_status="cancelled")
