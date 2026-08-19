"""Real tests for features/subscription_detective.py.

Tests below `# --- Real, live database tests` run against the real,
live Supabase database (`DEC-098`), mirroring `test_trust_digest.py`'s
established pattern. Every other test exercises the pure
`detect_subscriptions()` grouping logic directly -- zero database
dependency, real, deterministic inputs constructed by hand.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio

from quorum_backend.core import db
from quorum_backend.features.subscription_detective import (
    MIN_OCCURRENCES_TO_COUNT_AS_RECURRING,
    detect_subscriptions,
    fetch_detected_subscriptions,
)


def _at(day: int) -> datetime:
    return datetime(2026, 1, day, 12, 0, tzinfo=timezone.utc)


def test_a_payee_charged_only_once_is_not_detected_as_recurring():
    rows = [("Netflix", 649.0, _at(1))]
    results = detect_subscriptions(rows)
    assert results == []


def test_a_payee_charged_exactly_the_minimum_twice_is_detected():
    rows = [("Netflix", 649.0, _at(1)), ("Netflix", 649.0, _at(31))]
    results = detect_subscriptions(rows)
    assert len(results) == 1
    match = results[0]
    assert match.payee == "Netflix"
    assert match.occurrences == MIN_OCCURRENCES_TO_COUNT_AS_RECURRING
    assert match.average_amount == 649.0
    assert match.average_interval_days == 30.0


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
    # Two real gaps: 32 days, then 29 days -- averaged, not summed.
    assert match.average_interval_days == round((32 + 29) / 2, 1)


def test_multiple_distinct_payees_are_each_grouped_independently():
    rows = [
        ("Netflix", 649.0, _at(1)),
        ("Netflix", 649.0, _at(31)),
        ("A one-off vendor", 5000.0, _at(5)),
        ("Spotify", 119.0, _at(2)),
        ("Spotify", 119.0, _at(2) + timedelta(days=30)),
    ]
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
    rows = [
        ("Cheap Service", 50.0, _at(1)),
        ("Cheap Service", 50.0, _at(31)),
        ("Expensive Service", 5000.0, _at(1)),
        ("Expensive Service", 5000.0, _at(31)),
    ]
    results = detect_subscriptions(rows)
    assert [r.payee for r in results] == ["Expensive Service", "Cheap Service"]


def test_a_real_zero_day_gap_between_two_same_day_charges_is_handled_honestly():
    # Two genuinely real charges to the same payee on the same real day
    # -- a real, valid edge case (a split payment, a refund-and-rebill),
    # never a crash, honestly reported as a zero-day average interval.
    rows = [("Odd Vendor", 100.0, _at(1)), ("Odd Vendor", 100.0, _at(1))]
    results = detect_subscriptions(rows)
    assert len(results) == 1
    assert results[0].average_interval_days == 0.0


def test_an_empty_real_input_produces_a_real_empty_list_never_a_crash():
    assert detect_subscriptions([]) == []


# --- Real, live database tests -------------------------------------------


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


async def _insert_test_expense(pool, expense_id, *, payee, amount, occurred_at, user_id=None, source="manual"):
    await pool.execute(
        """
        INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        expense_id,
        user_id or uuid.uuid4(),
        payee,
        amount,
        occurred_at,
        source,
    )


async def test_fetch_detected_subscriptions_is_real_and_live_against_the_real_database(pool):
    # A real, deliberately obscure payee name -- can never collide with
    # real production data.
    payee = f"Real Test Subscription Vendor {uuid.uuid4()}"
    ids = [uuid.uuid4(), uuid.uuid4()]

    try:
        await _insert_test_expense(pool, ids[0], payee=payee, amount=299.00, occurred_at=_at(1))
        await _insert_test_expense(pool, ids[1], payee=payee, amount=299.00, occurred_at=_at(31))

        results = await fetch_detected_subscriptions(pool)
        match = next(r for r in results if r.payee == payee)

        assert match.occurrences == 2
        assert match.average_amount == 299.0
        assert match.average_interval_days == 30.0
    finally:
        await pool.execute("DELETE FROM expenses WHERE expense_id = ANY($1::uuid[])", ids)
