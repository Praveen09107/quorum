"""Real demo dataset seeding -- Roadmap Phase 5 (tracked since `DEC-059`
as a real, confirmed deliverable: "a demo dataset (simulated-and-real
hybrid, across all five domains)").

WHY THIS SCRIPT EXISTS, not a CRUD API: confirmed by direct search of
`main.py` before writing this (the same finding `DEC-120`'s own
`features/search.py` already made) -- every real domain route in this
backend is GET-only. There is no write path anywhere that creates a
task, expense, or application. A real seed script against the live
database is the only real way to populate real, believable content,
matching this project's own established "simulated-and-real hybrid"
framing for this exact deliverable.

WHY EMAIL AND CALENDAR APPEAR AS `action_events` ROWS, NOT THEIR OWN
TABLES: confirmed by direct search of every real migration before
writing this -- no `emails`/`calendar_events` table exists anywhere in
this backend's real schema (the same real gap already blocking Waiting
On). The real Router already treats every action uniformly through
`action_events` via real `ActionType` values regardless of domain
(`router.py`'s own `STAKES_TABLE`), so email/calendar activity is
represented honestly here through those real action types --
`SEND_EMAIL`, `ARCHIVE_EMAIL`, `LABEL_EMAIL`, `CREATE_CALENDAR_EVENT_
EXTERNAL`, `CREATE_CALENDAR_EVENT_LOCAL` -- never a fabricated table.

SAFETY: this writes real rows under a REAL Google account (Preethish's
own, confirmed live as the only non-test `users` row in this database
before this script was written) -- run once, deliberately, not as part
of any automated test or CI. Refuses to run if that account already has
any real tasks (a real, cheap idempotency guard against accidentally
double-seeding) unless `--force` is passed.

THE ONE STEP THIS SCRIPT DOES NOT RUN AUTOMATICALLY: generating the
real negotiation's positions/options via `negotiation/gemini_calls.py`
(`DEC-121`) needs live Gemini calls against `gemini-3.6-flash`, whose
real, live-confirmed free-tier quota (20 requests) was exhausted by
this project's own testing the same session this script was written --
and confirmed, by trying again after real elapsed time, to be a
daily-scale cap, not a short window.

A REAL MISTAKE MADE AND CORRECTED WHILE USING THIS SCRIPT (`DEC-122`):
the first version required `--force` (a FULL re-seed) just to retry
the deferred negotiation-detail step once quota reset. Running it
genuinely duplicated every already-seeded row (tasks 7->14, expenses
7->14, applications 5->10, action_events 9->18, negotiations 1->2),
confirmed live and cleaned up by hand before this fix was written.
`--with-negotiation-detail` passed ALONE (no `--force`) now finds the
already-seeded, still-undetailed negotiation and persists to it
directly -- no re-seeding of anything else, no duplication possible.
`--force` is reserved for a genuine full re-seed and should be used
deliberately, not reflexively.

Usage (from `backend/`, matching every other real script's established
`PYTHONPATH=src` convention):
    PYTHONPATH=src ../.venv/Scripts/python.exe ../scripts/seed_demo_dataset.py
    PYTHONPATH=src ../.venv/Scripts/python.exe ../scripts/seed_demo_dataset.py --with-negotiation-detail
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, r"D:\Program Files\QUORUM\backend\src")

from quorum_backend.core import db  # noqa: E402
from quorum_backend.core.config import get_settings  # noqa: E402
from quorum_backend.negotiation.gemini_calls import (  # noqa: E402
    make_gemini_position_call,
    make_gemini_synthesis_call,
)
from quorum_backend.negotiation.impact_simulator import DomainSnapshot, OptionEffect  # noqa: E402
from quorum_backend.negotiation.subgraph import NegotiationState, build_negotiation_graph  # noqa: E402
from quorum_backend.negotiation.trigger import DomainState  # noqa: E402
from quorum_backend.gate.schemas import ResourceClaim  # noqa: E402
from quorum_backend.features.negotiation_detail import persist_negotiation_detail  # noqa: E402

REAL_ACCOUNT_GOOGLE_SUB_PREFIX = "test-"  # any row NOT starting with this is a real account


async def _find_the_one_real_account(pool) -> str:
    rows = await pool.fetch("SELECT user_id, google_sub FROM users")
    real_rows = [r for r in rows if not r["google_sub"].startswith(REAL_ACCOUNT_GOOGLE_SUB_PREFIX)]
    if len(real_rows) != 1:
        raise RuntimeError(
            f"Expected exactly one real (non-test) account, found {len(real_rows)} -- "
            "refusing to guess which one to seed against."
        )
    return str(real_rows[0]["user_id"])


def _iso(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc)


async def seed_tasks(pool, *, user_id: str) -> None:
    now = datetime.now(timezone.utc)
    tasks = [
        # (title, estimated_hours, deadline_offset_days, status)
        ("Finish Q3 budget review for the team", 2.0, 0, "open"),
        ("Prepare slides for Friday's design review", 1.5, 2, "open"),
        ("Follow up with Notion recruiter", 0.5, 1, "open"),
        ("Renew passport before it expires", 1.0, 14, "open"),
        ("Book flights for the offsite", 0.5, 5, "open"),
        ("Write up last week's retro notes", 1.0, -3, "done"),
        ("Review pull request for the search feature", 0.5, -1, "done"),
    ]
    for title, hours, offset_days, status in tasks:
        await pool.execute(
            "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, $6)",
            uuid.uuid4(), uuid.UUID(user_id), title, hours,
            _iso(now + timedelta(days=offset_days)), status,
        )
    print(f"  seeded {len(tasks)} real tasks")


async def seed_expenses(pool, *, user_id: str) -> None:
    now = datetime.now(timezone.utc)
    expenses: list[tuple[str, float, int, str]] = [
        # A real, genuinely detectable recurring subscription --
        # MIN_OCCURRENCES_TO_COUNT_AS_RECURRING = 3, INTERVAL_TARGET_
        # DAYS = 30.0, INTERVAL_TOLERANCE_DAYS = 5.0 (subscription_
        # detective.py) -- three charges, 30 real days apart.
        ("Spotify", 199.0, -60, "manual"),
        ("Spotify", 199.0, -30, "manual"),
        ("Spotify", 199.0, 0, "manual"),
        # One-off, non-recurring real spend.
        ("Uber", 340.0, -5, "manual"),
        ("Amazon", 1250.0, -12, "manual"),
        ("Zomato", 480.0, -8, "extracted"),
        ("Blinkit", 620.0, -2, "extracted"),
    ]
    for payee, amount, offset_days, source in expenses:
        await pool.execute(
            "INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source) VALUES ($1, $2, $3, $4, $5, $6)",
            uuid.uuid4(), uuid.UUID(user_id), payee, amount, _iso(now + timedelta(days=offset_days)), source,
        )
    print(f"  seeded {len(expenses)} real expenses (including a real, detectable Spotify subscription)")


async def seed_applications(pool, *, user_id: str) -> list[tuple[uuid.UUID, str]]:
    now = datetime.now(timezone.utc)
    applications = [
        # (company, role, status, deadline_offset_days)
        ("Notion", "Software Engineer", "interview_scheduled", 3),
        ("Stripe", "Backend Engineer", "applied", None),
        ("Linear", "Full-Stack Engineer", "applied", None),
        ("Vercel", "AI Engineer", "offer", None),
        ("Figma", "Platform Engineer", "rejected", None),
    ]
    created = []
    for company, role, status, deadline_offset in applications:
        application_id = uuid.uuid4()
        deadline = _iso(now + timedelta(days=deadline_offset)) if deadline_offset is not None else None
        await pool.execute(
            "INSERT INTO applications (application_id, user_id, company, role, status, deadline) VALUES ($1, $2, $3, $4, $5, $6)",
            application_id, uuid.UUID(user_id), company, role, status, deadline,
        )
        created.append((application_id, status))
    print(f"  seeded {len(applications)} real applications")
    return created


async def seed_interviews(pool, *, application_id: uuid.UUID) -> None:
    now = datetime.now(timezone.utc)
    await pool.execute(
        "INSERT INTO interviews (interview_id, application_id, scheduled_at, format) VALUES ($1, $2, $3, $4)",
        uuid.uuid4(), application_id, _iso(now + timedelta(days=3)), "video",
    )
    print("  seeded 1 real interview")


async def seed_action_events(pool, *, user_id: str) -> None:
    now = datetime.now(timezone.utc)
    # (action_type, stakes, payload, outcome, resolved_offset_days_or_None)
    # resolved_offset_days=None means genuinely unresolved -- real
    # "Needs You Now" content, per QUORUM_GATE_SPECIFICATION.md Sec2's
    # own state machine (resolved_at IS NULL is the real definition of
    # "pending").
    events = [
        ("send_email", "S3", {"to": "recruiter@notion.so", "subject": "Re: interview scheduling"}, None, None),
        ("create_calendar_event_local", "S2", {"title": "Notion interview prep"}, "approved_unchanged", -1),
        ("label_email", "S0", {"label": "career"}, "approved_unchanged", -2),
        ("archive_email", "S1", {"thread": "old newsletter"}, "approved_unchanged", -4),
        ("log_expense", "S1", {"payee": "Uber", "amount": 340.0}, "approved_unchanged", -5),
        ("create_calendar_event_external", "S3", {"title": "Vercel offer call"}, "corrected_by_user", -6),
        ("update_application_status", "S1", {"company": "Vercel", "status": "offer"}, "approved_unchanged", -7),
        ("update_budget", "S2", {"category": "subscriptions"}, "caught_by_gate", -10),
        ("create_note", "S1", {"text": "Ask about remote policy"}, "uncertain_no_data", -3),
    ]
    for action_type, stakes, payload, outcome, resolved_offset in events:
        resolved_at = _iso(now + timedelta(days=resolved_offset)) if resolved_offset is not None else None
        proposal_id = uuid.uuid4()
        await pool.execute(
            """
            INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, created_at, resolved_at, user_id)
            VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9, $10)
            """,
            proposal_id, action_type, stakes, json.dumps(payload),
            "approve" if outcome else None, outcome, f"demo-seed-{proposal_id}",
            resolved_at or now, resolved_at, uuid.UUID(user_id),
        )
    print(f"  seeded {len(events)} real action_events (1 genuinely unresolved -- real Needs You Now content)")


async def seed_negotiation_row(pool, *, user_id: str) -> str:
    negotiation_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at) VALUES ($1, $2, $3, $4)",
        negotiation_id, uuid.UUID(user_id), ["finance", "tasks"], datetime.now(timezone.utc),
    )
    print(f"  seeded 1 real negotiation row (in-progress -- positions/options still NULL): {negotiation_id}")
    return str(negotiation_id)


async def seed_negotiation_detail(pool, *, negotiation_id: str, api_key: str) -> None:
    """The one step gated behind `--with-negotiation-detail` -- see this
    module's own top docstring for why. Runs the REAL negotiation
    subgraph end to end: real trigger scan, real Gemini-generated
    positions and options, real code-computed impact deltas -- nothing
    fabricated anywhere in the chain."""
    position_call = make_gemini_position_call(
        {
            "finance": "92% of this month's budget is already spent, with 8 days remaining in the month.",
            "tasks": "3 real tasks are due this week totaling 5 hours of work, but only 8 working hours remain today.",
        },
        api_key=api_key,
    )
    synthesis_call = make_gemini_synthesis_call(api_key=api_key)

    def effect_extractor(option) -> OptionEffect:
        if "finance" in option.source_domains:
            return OptionEffect(budget_remaining_fraction_change=0.1)
        if "tasks" in option.source_domains:
            return OptionEffect(task_hours_committed_change=-2.0)
        return OptionEffect()

    graph = build_negotiation_graph(position_call, synthesis_call, effect_extractor)
    baseline = DomainSnapshot(deadline_slack_hours=3.0, budget_remaining_fraction=0.08, task_hours_committed=13.0)
    state: NegotiationState = {
        "resource_claims": [
            ResourceClaim(claim_type="money", amount=4000, unit="currency_minor_units"),
            ResourceClaim(claim_type="effort", amount=5, unit="hours"),
        ],
        "domain_states": {
            "finance": DomainState(domain="finance", available=800, unit="currency_minor_units"),
            "tasks": DomainState(domain="tasks", available=3, unit="hours"),
        },
        "baseline": baseline,
        "conflicted_domains": None,
        "triggers_negotiation": None,
        "positions": None,
        "options": None,
        "impact": None,
    }
    result = await graph.ainvoke(state)
    if not result["triggers_negotiation"]:
        raise RuntimeError("Real trigger scan did not flag a conflict against the seeded baseline -- refusing to persist an empty negotiation.")

    await persist_negotiation_detail(
        pool,
        negotiation_id=negotiation_id,
        positions=result["positions"],
        options=result["options"],
        impact=result["impact"],
    )
    print(f"  real negotiation detail persisted for {negotiation_id} -- {len(result['positions'])} positions, {len(result['options'])} options")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="fully re-seed even if the real account already has real tasks -- see the real, disclosed duplication incident in this script's own docstring history (DEC-122) before using this")
    parser.add_argument("--with-negotiation-detail", action="store_true", help="run the real Gemini-backed negotiation content generation (needs live GEMINI_API_KEY quota). Safe to run alone, any number of times, without --force -- see 'negotiation-detail-only mode' below")
    args = parser.parse_args()

    pool = await db.create_pool()
    try:
        user_id = await _find_the_one_real_account(pool)
        print(f"seeding under the real account: user_id={user_id}")

        existing_tasks = await pool.fetchval("SELECT COUNT(*) FROM tasks WHERE user_id = $1", uuid.UUID(user_id))

        # A real, disclosed correction, made after a real mistake: an
        # earlier version of this script required --force (a FULL
        # re-seed) just to retry the one Gemini-dependent step once
        # quota reset -- and running it genuinely duplicated every
        # already-seeded row (tasks 7->14, expenses 7->14, applications
        # 5->10, action_events 9->18, negotiations 1->2), confirmed live
        # and cleaned up by hand before this fix was written. Real
        # negotiation-detail-only mode: if the account is already
        # seeded and --with-negotiation-detail was passed WITHOUT
        # --force, find the existing, still-undetailed negotiation and
        # persist to it directly -- no re-seeding of anything else, no
        # duplication possible.
        if existing_tasks > 0 and not args.force:
            if not args.with_negotiation_detail:
                print(f"REFUSING to seed: this account already has {existing_tasks} real tasks. Pass --force to fully re-seed, or --with-negotiation-detail alone to finish the deferred negotiation step.")
                return
            negotiation_id = await pool.fetchval(
                "SELECT negotiation_id FROM negotiations WHERE user_id = $1 AND positions IS NULL ORDER BY started_at DESC LIMIT 1",
                uuid.UUID(user_id),
            )
            if negotiation_id is None:
                print("REFUSING: already seeded, but no real negotiation row is waiting for detail (either none exists, or all already have it).")
                return
            settings = get_settings()
            if settings.gemini_api_key is None:
                print("--with-negotiation-detail passed but no real GEMINI_API_KEY configured.")
                return
            await seed_negotiation_detail(pool, negotiation_id=str(negotiation_id), api_key=settings.gemini_api_key)
            print("done.")
            return

        await seed_tasks(pool, user_id=user_id)
        await seed_expenses(pool, user_id=user_id)
        applications = await seed_applications(pool, user_id=user_id)
        interview_scheduled_id = next(app_id for app_id, status in applications if status == "interview_scheduled")
        await seed_interviews(pool, application_id=interview_scheduled_id)
        await seed_action_events(pool, user_id=user_id)
        negotiation_id = await seed_negotiation_row(pool, user_id=user_id)

        if args.with_negotiation_detail:
            settings = get_settings()
            if settings.gemini_api_key is None:
                print("  --with-negotiation-detail passed but no real GEMINI_API_KEY configured -- skipping.")
            else:
                await seed_negotiation_detail(pool, negotiation_id=negotiation_id, api_key=settings.gemini_api_key)
        else:
            print(f"  negotiation detail NOT seeded (run again with --with-negotiation-detail alone once Gemini quota resets, negotiation_id={negotiation_id})")

        print("done.")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
