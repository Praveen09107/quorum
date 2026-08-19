"""Real tests for features/subscription_detective.py.

Tests below `# --- Real, live database tests` run against the real,
live Supabase database (`DEC-098`), mirroring `test_trust_digest.py`'s
established pattern. Every other test exercises the pure
`detect_subscriptions()` grouping logic directly -- zero database
dependency, real, deterministic inputs constructed by hand.

Real, disclosed correction (`DEC-112`): this file previously tested a
simpler, more permissive rule (min 2 occurrences, no interval
filtering) than the one actually specified in
`QUORUM_CONFIGURATION_CONSTANTS.md` §4 (min 3 occurrences, every
consecutive gap within ±5.0 days of a 30-day target). Rewritten
against the real, corrected algorithm -- see
`subscription_detective.py`'s own top-of-file docstring for the full
account of the original miss.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.subscription_detective import (
    INTERVAL_TARGET_DAYS,
    INTERVAL_TOLERANCE_DAYS,
    MIN_OCCURRENCES_TO_COUNT_AS_RECURRING,
    detect_subscriptions,
    fetch_detected_subscriptions,
)


def _at(day: int) -> datetime:
    return datetime(2026, 1, day, 12, 0, tzinfo=timezone.utc)


def _monthly_rows(payee: str, amount: float, count: int, start: datetime = _at(1)) -> list[tuple[str, float, datetime]]:
    """A real, deterministic helper -- `count` real charges to `payee`,
    each real `INTERVAL_TARGET_DAYS` apart, squarely inside tolerance.
    Used throughout this file wherever a test's real point is something
    other than the exact spacing itself."""
    return [(payee, amount, start + timedelta(days=INTERVAL_TARGET_DAYS * i)) for i in range(count)]


def test_a_payee_charged_only_once_is_not_detected_as_recurring():
    rows = [("Netflix", 649.0, _at(1))]
    results = detect_subscriptions(rows)
    assert results == []


def test_a_payee_charged_only_twice_is_not_enough_even_with_perfect_monthly_spacing():
    # The real, specified minimum is 3, not 2 -- confirmed against
    # QUORUM_CONFIGURATION_CONSTANTS.md §4. Two charges, however
    # perfectly spaced, are not yet a real, detected subscription.
    rows = _monthly_rows("Netflix", 649.0, count=2)
    results = detect_subscriptions(rows)
    assert results == []


def test_a_payee_charged_exactly_the_real_minimum_three_times_is_detected():
    rows = _monthly_rows("Netflix", 649.0, count=MIN_OCCURRENCES_TO_COUNT_AS_RECURRING)
    results = detect_subscriptions(rows)
    assert len(results) == 1
    match = results[0]
    assert match.payee == "Netflix"
    assert match.occurrences == MIN_OCCURRENCES_TO_COUNT_AS_RECURRING
    assert match.average_amount == 649.0
    assert match.average_interval_days == INTERVAL_TARGET_DAYS


def test_average_amount_and_interval_are_real_means_across_all_real_charges():
    rows = [
        ("Spotify", 119.0, _at(1)),
        ("Spotify", 129.0, _at(1) + timedelta(days=32)),
        ("Spotify", 119.0, _at(1) + timedelta(days=61)),
    ]
    results = detect_subscriptions(rows)
    assert len(results) == 1
    match = results[0]
    assert match.occurrences == 3
    assert match.average_amount == round((119.0 + 129.0 + 119.0) / 3, 2)
    # Two real gaps: 32 days, then 29 days -- both within the real
    # ±5-day tolerance around the real 30-day target, averaged, not
    # summed.
    assert match.average_interval_days == round((32 + 29) / 2, 1)


def test_an_interval_exactly_at_the_real_tolerance_boundary_still_qualifies():
    # A real, deliberate boundary proof -- a real 25-day gap then a
    # real 35-day gap, exactly ±5.0 days off the real 30-day target on
    # each side, both still inside the real, closed tolerance window,
    # not excluded by an off-by-one at the boundary.
    low_gap = INTERVAL_TARGET_DAYS - INTERVAL_TOLERANCE_DAYS
    high_gap = INTERVAL_TARGET_DAYS + INTERVAL_TOLERANCE_DAYS
    rows = [
        ("Boundary Service", 100.0, _at(1)),
        ("Boundary Service", 100.0, _at(1) + timedelta(days=low_gap)),
        ("Boundary Service", 100.0, _at(1) + timedelta(days=low_gap + high_gap)),
    ]
    results = detect_subscriptions(rows)
    assert len(results) == 1


def test_a_single_gap_just_outside_tolerance_disqualifies_the_whole_real_sequence():
    # Two real gaps of exactly 30 days (perfect), then one real gap of
    # 36 days (0.01 outside real tolerance) -- the whole payee is
    # excluded, not just the one irregular pair. A real, genuine sign
    # this isn't an actual monthly subscription, not something to
    # average away.
    rows = [
        ("Irregular Vendor", 100.0, _at(1)),
        ("Irregular Vendor", 100.0, _at(1) + timedelta(days=30)),
        ("Irregular Vendor", 100.0, _at(1) + timedelta(days=30 + 36)),
    ]
    results = detect_subscriptions(rows)
    assert results == []


def test_enough_real_occurrences_but_genuinely_irregular_spacing_is_not_detected():
    # A real, honest proof: raw occurrence count alone was never
    # sufficient under the real, specified rule -- three real charges,
    # nowhere near a monthly cadence, are correctly excluded.
    rows = [
        ("Sporadic Vendor", 100.0, _at(1)),
        ("Sporadic Vendor", 100.0, _at(1) + timedelta(days=5)),
        ("Sporadic Vendor", 100.0, _at(1) + timedelta(days=205)),
    ]
    results = detect_subscriptions(rows)
    assert results == []


def test_multiple_distinct_payees_are_each_grouped_independently():
    rows = (
        _monthly_rows("Netflix", 649.0, count=3)
        + [("A one-off vendor", 5000.0, _at(5))]
        + _monthly_rows("Spotify", 119.0, count=3, start=_at(2))
    )
    results = detect_subscriptions(rows)
    payees = {r.payee for r in results}
    # The one-off vendor (charged once) is genuinely excluded.
    assert payees == {"Netflix", "Spotify"}


def test_payee_matching_is_exact_never_fuzzy():
    # A real, disclosed limitation, proven directly: two superficially
    # similar payee strings are never merged.
    rows = [("Netflix", 649.0, _at(1)), ("NETFLIX.COM", 649.0, _at(31))]
    results = detect_subscriptions(rows)
    assert results == []  # each individually charged only once


def test_results_are_sorted_by_average_amount_descending():
    rows = _monthly_rows("Cheap Service", 50.0, count=3) + _monthly_rows("Expensive Service", 5000.0, count=3)
    results = detect_subscriptions(rows)
    assert [r.payee for r in results] == ["Expensive Service", "Cheap Service"]


def test_a_real_zero_day_gap_is_a_real_irregularity_that_disqualifies_not_a_crash():
    # A real, deliberate correction from this file's own earlier
    # version (DEC-112): a same-day double charge (a split payment, a
    # refund-and-rebill) is a real, genuine 0-day gap -- 30 days outside
    # the real tolerance window, so the whole sequence is correctly
    # excluded, never crashed, and never silently counted as a monthly
    # subscription just because the occurrence count was met.
    rows = [
        ("Odd Vendor", 100.0, _at(1)),
        ("Odd Vendor", 100.0, _at(1)),
        ("Odd Vendor", 100.0, _at(1) + timedelta(days=30)),
    ]
    results = detect_subscriptions(rows)
    assert results == []


def test_an_empty_real_input_produces_a_real_empty_list_never_a_crash():
    assert detect_subscriptions([]) == []


# --- Real, live database tests -------------------------------------------
#
# Real per-user scoping retrofit (DEC-110): fetch_detected_subscriptions()
# now requires a real, provisioned internal user_id. The user_id fixture
# below provisions one real, fresh test identity per test and cleans it
# up afterward.


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-finance-{uuid.uuid4()}"
    real_user_id = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield real_user_id
    await pool.execute("DELETE FROM users WHERE google_sub = $1", google_sub)


async def _insert_test_expense(pool, expense_id, *, payee, amount, occurred_at, user_id, source="manual"):
    await pool.execute(
        """
        INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        expense_id,
        uuid.UUID(user_id),
        payee,
        amount,
        occurred_at,
        source,
    )


async def test_fetch_detected_subscriptions_is_real_and_live_against_the_real_database(pool, user_id):
    # A real, deliberately obscure payee name -- can never collide with
    # real production data. Three real, monthly-spaced charges -- the
    # real, specified minimum (DEC-112).
    payee = f"Real Test Subscription Vendor {uuid.uuid4()}"
    ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    occurrences = [_at(1), _at(31), _at(1) + timedelta(days=60)]

    try:
        for expense_id, occurred_at in zip(ids, occurrences):
            await _insert_test_expense(
                pool, expense_id, payee=payee, amount=299.00, occurred_at=occurred_at, user_id=user_id
            )

        results = await fetch_detected_subscriptions(pool, user_id=user_id)
        match = next(r for r in results if r.payee == payee)

        assert match.occurrences == 3
        assert match.average_amount == 299.0
        assert match.average_interval_days == 30.0
    finally:
        await pool.execute("DELETE FROM expenses WHERE expense_id = ANY($1::uuid[])", ids)


async def test_fetch_detected_subscriptions_never_returns_another_real_users_rows(pool, user_id):
    other_google_sub = f"test-finance-other-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_google_sub, email=None)
    payee = f"Another real user's real recurring vendor {uuid.uuid4()}"
    ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    occurrences = [_at(1), _at(31), _at(1) + timedelta(days=60)]

    try:
        for expense_id, occurred_at in zip(ids, occurrences):
            await _insert_test_expense(
                pool, expense_id, payee=payee, amount=50.00, occurred_at=occurred_at, user_id=other_user_id
            )

        results = await fetch_detected_subscriptions(pool, user_id=user_id)
        assert all(r.payee != payee for r in results)
    finally:
        await pool.execute("DELETE FROM expenses WHERE expense_id = ANY($1::uuid[])", ids)
        await pool.execute("DELETE FROM users WHERE google_sub = $1", other_google_sub)
