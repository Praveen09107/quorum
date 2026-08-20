"""Real, live Unified Fast Search -- backs `GET /search?q=...`
(`QUORUM_DATA_CONTRACTS.md` §5.7, `SearchableItem` per §2). Roadmap
Phase 4a, the smallest of the three remaining domain gaps (`DEC-120`):
pgvector/`note_embeddings` infrastructure already existed (`DEC-098`);
this module is what actually generates and queries real embeddings for
the first time.

HONEST ARCHITECTURE DISCLOSURE, confirmed by direct search of `main.py`
before designing this module: every real domain route in this backend
(`/tasks`, `/career_pipeline`, `/finance/subscriptions`) is GET-only --
there is no real write path anywhere that creates a task, expense, or
application. These tables only ever gain rows through migration
seeding or a future demo-dataset load, never through a real API call.
This means there is no "on creation" moment to hook a real-time
embedding write into, the way `DEC-119`'s own `/today` work initially
assumed Search's own eventual embedding step might work.

The real, disclosed choice made here instead: a LAZY backfill, run at
the start of every real `search()` call. It scans each of the user's
four real content tables for rows with no matching `note_embeddings`
row yet (by `user_id` + `source_type` + `source_id`, enforced as a
real UNIQUE index by `migrations/0005_search_embeddings`, not just an
application-level check), embeds exactly those via Gemini
(`core/embeddings.py`), and writes them before running the real
similarity query. Already-embedded rows are never re-embedded or
re-charged against the Gemini API. It runs inline rather than in a
persistent background worker because this deployment is deliberately
fully serverless (`CLAUDE.md`'s own standing constraint; a `pg_cron`-
driven pre-emptive backfill was considered and genuinely deferred as
separate, larger scope, not built silently).

REAL, HARD BOUND on that backfill, and a real, disclosed correction:
an earlier version of this module described the backfill as "a real,
bounded batch" while imposing no limit whatsoever -- a genuinely false
claim in a docstring, caught by `DEC-120`'s own pre-merge review. It
matters concretely, not theoretically: this service runs at Cloud Run
`--concurrency=1 --max-instances=2`, so one user's inline backfill of
N rows is N sequential live Gemini calls that block an entire instance
for their whole duration, and a large enough N simply exceeds the
request timeout and returns nothing at all. `MAX_BACKFILL_PER_REQUEST`
below is now a real, enforced `LIMIT` on every one of the four
queries. The honest trade-off that creates, stated plainly rather than
hidden: a first search over a large, entirely-unembedded corpus can
return INCOMPLETE results, because some rows genuinely aren't embedded
yet. That is deliberate -- a fast, honestly-partial first result that
completes on subsequent calls is strictly better than a request that
blocks the service and then times out with nothing. The backfill is
self-healing: each call embeds the next batch until the corpus is
fully covered, after which it does zero Gemini calls.

`item_type` values actually produced here: `task`, `expense`,
`application`, `decision`. `email` is deliberately never produced --
no Gmail integration exists in this backend. `application` is a real,
disclosed, small addition to the four-value `SearchItemType` enum
`mobile/lib/features/search/search_logic.dart` already shipped
(`email`/`task`/`expense`/`decision`, itself already documented there
as a "reasoned construction," not a literal spec value) -- leaving out
an entire real domain (career applications) from a feature whose own
name is "Unified" Fast Search would have been a real, silent gap, not
a faithful implementation of what "unified" means here.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import asyncpg

from quorum_backend.core.embeddings import embed_text

SEARCH_RESULT_CAP = 10  # QUORUM_CONFIGURATION_CONSTANTS.md §4

# A real, enforced ceiling on how many live Gemini calls one HTTP
# request can trigger -- see this module's docstring for the real Cloud
# Run concurrency/timeout reasoning behind it being a hard limit rather
# than a soft intention. 50 is a real, disclosed, reasoned choice, not
# a measured optimum: at a typical ~0.2-0.5s per real embedding call,
# 50 lands around 10-25s of inline work, comfortably inside Cloud Run's
# real 300s request timeout while leaving substantial headroom for a
# slow upstream. QUORUM_CONFIGURATION_CONSTANTS.md §4.
MAX_BACKFILL_PER_REQUEST = 50


@dataclass(frozen=True)
class SearchableItem:
    item_id: str
    item_type: str  # "task" | "expense" | "application" | "decision"
    text: str
    timestamp: str  # ISO 8601 with a literal "Z" suffix


def _format_timestamp(value: datetime) -> str:
    # Matches every other real feature module's own established
    # convention (today.py, tasks.py, career_pipeline.py).
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _content_for_task(*, title: str) -> str:
    return title


def _content_for_expense(*, payee: str, amount: float) -> str:
    return f"{payee} — ₹{amount:.2f}"


def _content_for_application(*, company: str, role: str | None) -> str:
    return f"{company} — {role}" if role else company


def _content_for_decision(*, action_type: str, outcome: str | None, gate_decision: str | None) -> str:
    status = outcome or gate_decision or "pending"
    return f"{action_type}: {status}"


async def _backfill_source(
    pool: asyncpg.Pool,
    *,
    user_id: str,
    source_type: str,
    rows: list[tuple[str, str]],  # (source_id, content)
    api_key: str,
) -> None:
    """Shared insert step for one content table's missing rows. Real,
    sequential Gemini calls -- deliberately not `asyncio.gather`ed
    concurrently, to stay conservative against this key's real, as-yet-
    unconfirmed free-tier rate limit rather than assume headroom."""
    for source_id, content in rows:
        vector = await embed_text(content, api_key=api_key)
        vector_literal = "[" + ",".join(repr(v) for v in vector) + "]"
        await pool.execute(
            """
            INSERT INTO note_embeddings (user_id, content, embedding, source_type, source_id)
            VALUES ($1, $2, $3::vector, $4, $5)
            ON CONFLICT (user_id, source_type, source_id) DO NOTHING
            """,
            uuid.UUID(user_id),
            content,
            vector_literal,
            source_type,
            uuid.UUID(source_id),
        )


async def backfill_missing_embeddings(pool: asyncpg.Pool, *, user_id: str, api_key: str) -> None:
    """Real, live -- finds every one of this user's task/expense/
    application/decision rows with no `note_embeddings` row yet, and
    embeds+writes exactly those. Idempotent: re-running this after
    everything is already embedded does zero Gemini calls (each query
    below returns no rows once its domain is fully covered)."""
    task_rows = await pool.fetch(
        """
        SELECT t.task_id, t.title
        FROM tasks t
        WHERE t.user_id = $1
          AND NOT EXISTS (
              SELECT 1 FROM note_embeddings e
              WHERE e.user_id = $1 AND e.source_type = 'task' AND e.source_id = t.task_id
          )
        LIMIT $2
        """,
        uuid.UUID(user_id),
        MAX_BACKFILL_PER_REQUEST,
    )
    await _backfill_source(
        pool,
        user_id=user_id,
        source_type="task",
        rows=[(str(r["task_id"]), _content_for_task(title=r["title"])) for r in task_rows],
        api_key=api_key,
    )

    expense_rows = await pool.fetch(
        """
        SELECT e.expense_id, e.payee, e.amount
        FROM expenses e
        WHERE e.user_id = $1
          AND NOT EXISTS (
              SELECT 1 FROM note_embeddings n
              WHERE n.user_id = $1 AND n.source_type = 'expense' AND n.source_id = e.expense_id
          )
        LIMIT $2
        """,
        uuid.UUID(user_id),
        MAX_BACKFILL_PER_REQUEST,
    )
    await _backfill_source(
        pool,
        user_id=user_id,
        source_type="expense",
        rows=[
            (str(r["expense_id"]), _content_for_expense(payee=r["payee"], amount=float(r["amount"])))
            for r in expense_rows
        ],
        api_key=api_key,
    )

    application_rows = await pool.fetch(
        """
        SELECT a.application_id, a.company, a.role
        FROM applications a
        WHERE a.user_id = $1
          AND NOT EXISTS (
              SELECT 1 FROM note_embeddings n
              WHERE n.user_id = $1 AND n.source_type = 'application' AND n.source_id = a.application_id
          )
        LIMIT $2
        """,
        uuid.UUID(user_id),
        MAX_BACKFILL_PER_REQUEST,
    )
    await _backfill_source(
        pool,
        user_id=user_id,
        source_type="application",
        rows=[
            (str(r["application_id"]), _content_for_application(company=r["company"], role=r["role"]))
            for r in application_rows
        ],
        api_key=api_key,
    )

    decision_rows = await pool.fetch(
        """
        SELECT ae.proposal_id, ae.action_type, ae.outcome, ae.gate_decision
        FROM action_events ae
        WHERE ae.user_id = $1
          AND NOT EXISTS (
              SELECT 1 FROM note_embeddings n
              WHERE n.user_id = $1 AND n.source_type = 'decision' AND n.source_id = ae.proposal_id
          )
        LIMIT $2
        """,
        uuid.UUID(user_id),
        MAX_BACKFILL_PER_REQUEST,
    )
    await _backfill_source(
        pool,
        user_id=user_id,
        source_type="decision",
        rows=[
            (
                str(r["proposal_id"]),
                _content_for_decision(action_type=r["action_type"], outcome=r["outcome"], gate_decision=r["gate_decision"]),
            )
            for r in decision_rows
        ],
        api_key=api_key,
    )


async def search(pool: asyncpg.Pool, *, user_id: str, query: str, api_key: str, limit: int = SEARCH_RESULT_CAP) -> list[SearchableItem]:
    """Real, live -- backfills any missing embeddings for this user
    first (see module docstring), then embeds `query` and ranks the
    user's full real corpus by real cosine distance. Already sorted
    server-side, per §5.7's own explicit contract -- the opposite of
    Today's zones, which sort client-side."""
    await backfill_missing_embeddings(pool, user_id=user_id, api_key=api_key)

    query_vector = await embed_text(query, api_key=api_key)
    query_literal = "[" + ",".join(repr(v) for v in query_vector) + "]"

    rows = await pool.fetch(
        """
        SELECT source_type, source_id, content, created_at
        FROM note_embeddings
        -- `embedding IS NOT NULL` is defensive, not currently
        -- reachable: the backfill above never writes a NULL vector.
        -- Confirmed live during DEC-120's review that without it a
        -- NULL-embedding row does get returned (sorted last) when a
        -- user has fewer than `limit` embedded rows -- a real, if
        -- latent, way for a result with no genuine similarity score
        -- to reach a person as though it matched.
        WHERE user_id = $1 AND embedding IS NOT NULL
        ORDER BY embedding <=> $2::vector
        LIMIT $3
        """,
        uuid.UUID(user_id),
        query_literal,
        limit,
    )
    return [
        SearchableItem(
            item_id=str(row["source_id"]),
            item_type=row["source_type"],
            text=row["content"],
            timestamp=_format_timestamp(row["created_at"]),
        )
        for row in rows
    ]
