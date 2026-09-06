"""Real tests for core/gemini_quota.py (`DEC-165`).

Error-path and fail-open tests (`# --- Deterministic, no real network`)
use monkeypatching, the same established discipline `test_embeddings.py`
already uses for cases a real, live external service cannot reliably
reproduce on demand (a configured-but-unreachable Redis, a genuinely
absent configuration). `# --- Deterministic enforcement logic` mocks
`_redis_command` directly (not `httpx`) to give the real `daily_limit`-
exceeded raise/DECR-on-reject branch genuine, deterministic coverage
that runs in CI too -- a real, disclosed gap this module's own
CRITICAL-tier review found: the four "Real, live" tests below cover
this same branch, but are all skipped in any environment without real
Upstash credentials configured, CI included.

The tests below `# --- Real, live Upstash Redis tests` call the actual,
live Upstash REST API with the real credentials in `backend/.env` --
per CLAUDE.md Rule 5, this is what actually proves the integration
works. Skipped, not failed, without real Upstash credentials
configured. Every real test uses a clearly-fake, dedicated model name
(`_unique_test_model()`, built from `_TEST_MODEL_PREFIX`, never a real
Gemini model id) so these tests never increment or interfere with the
REAL, shared, production `gemini-3.6-flash` counter this module exists
to protect -- and each real test deletes its own real key afterward,
per Rule 5's own established cleanup discipline."""
import uuid

import httpx
import pytest

from quorum_backend.core.config import get_settings
from quorum_backend.core.gemini_quota import (
    GeminiQuotaExhaustedError,
    _redis_command,
    _today_google_reset_date_string,
    reserve_gemini_quota_slot,
)

_HAS_REAL_REDIS = get_settings().upstash_redis_url is not None and get_settings().upstash_redis_rest_token is not None


# --- Deterministic, no real network ---


def test_today_google_reset_date_string_is_a_real_iso_date_shape():
    result = _today_google_reset_date_string()
    assert len(result) == 10
    assert result[4] == "-" and result[7] == "-"


async def test_reserve_gemini_quota_slot_fails_open_when_redis_is_not_configured(monkeypatch):
    class _FakeSettings:
        upstash_redis_url = None
        upstash_redis_rest_token = None

    monkeypatch.setattr("quorum_backend.core.gemini_quota.get_settings", lambda: _FakeSettings())

    # No real network call should even be attempted -- a real, live
    # call would fail loudly against a nonexistent host, so a clean
    # return here IS the real proof this path never reaches httpx.
    await reserve_gemini_quota_slot(model="any-model-irrelevant-here")


async def test_reserve_gemini_quota_slot_fails_open_when_a_real_redis_call_itself_fails(monkeypatch):
    class _FakeSettings:
        upstash_redis_url = "https://real-looking-but-unreachable.example.invalid"
        upstash_redis_rest_token = "fake-token-never-sent-anywhere-real"

    monkeypatch.setattr("quorum_backend.core.gemini_quota.get_settings", lambda: _FakeSettings())

    # A genuine DNS/connection failure against a real, live-shaped but
    # unreachable host -- proves the real try/except around the real
    # Redis call actually catches this class of failure and fails open,
    # rather than only working in the happy path.
    await reserve_gemini_quota_slot(model="any-model-irrelevant-here")


async def test_reserve_gemini_quota_slot_never_swallows_a_genuine_bug_in_this_modules_own_code(monkeypatch):
    """Real regression test for the exact real gap this module's own
    CRITICAL-tier review found live: an earlier, overly broad `except
    Exception` silently treated a genuine `AttributeError`/`TypeError`
    bug inside this module's own code identically to a real Upstash
    outage. The real, narrowed `except (httpx.HTTPError, KeyError,
    ValueError)` must let anything else -- a real bug, not a real
    infrastructure failure -- propagate loudly instead."""
    class _FakeSettings:
        upstash_redis_url = "https://real-looking.example.invalid"
        upstash_redis_rest_token = "fake-token-never-sent-anywhere-real"

    async def _broken_redis_command(*_parts, **_kwargs):
        raise TypeError("a genuine bug in this module's own code, not a real Redis failure")

    monkeypatch.setattr("quorum_backend.core.gemini_quota.get_settings", lambda: _FakeSettings())
    monkeypatch.setattr("quorum_backend.core.gemini_quota._redis_command", _broken_redis_command)

    with pytest.raises(TypeError):
        await reserve_gemini_quota_slot(model="any-model-irrelevant-here")


# --- Deterministic enforcement logic (mocked _redis_command, no real network, real CI coverage) ---


async def test_reserve_gemini_quota_slot_raises_when_the_mocked_count_exceeds_the_real_limit(monkeypatch):
    """Real, deterministic coverage of the `daily_limit`-exceeded raise
    branch -- the "Real, live" tests below cover this same real branch
    too, but are skipped everywhere without real Upstash credentials
    configured, CI included (a real, disclosed gap this module's own
    CRITICAL-tier review found). Mocking `_redis_command` directly
    (not `httpx`) exercises `reserve_gemini_quota_slot()`'s own real
    control flow deterministically, with no real network at all."""
    class _FakeSettings:
        upstash_redis_url = "https://real-looking.example.invalid"
        upstash_redis_rest_token = "fake-token-never-sent-anywhere-real"

    calls: list[tuple[str, ...]] = []

    async def _fake_redis_command(*parts, **_kwargs):
        calls.append(parts)
        if parts[0] == "INCR":
            return 21  # one over a real daily_limit of 20
        return 1  # DECR/EXPIRE's own real return shape -- value irrelevant here

    monkeypatch.setattr("quorum_backend.core.gemini_quota.get_settings", lambda: _FakeSettings())
    monkeypatch.setattr("quorum_backend.core.gemini_quota._redis_command", _fake_redis_command)

    with pytest.raises(GeminiQuotaExhaustedError):
        await reserve_gemini_quota_slot(model="any-model-irrelevant-here", daily_limit=20)

    # A real, deterministic proof of the DECR-on-reject fix: the
    # rejected reservation's own real slot is given back, not just
    # rejected and left inflating the counter forever.
    assert calls[-1][0] == "DECR"


async def test_reserve_gemini_quota_slot_never_calls_decr_when_within_the_real_limit(monkeypatch):
    class _FakeSettings:
        upstash_redis_url = "https://real-looking.example.invalid"
        upstash_redis_rest_token = "fake-token-never-sent-anywhere-real"

    calls: list[tuple[str, ...]] = []

    async def _fake_redis_command(*parts, **_kwargs):
        calls.append(parts)
        return 5  # well within a real daily_limit of 20

    monkeypatch.setattr("quorum_backend.core.gemini_quota.get_settings", lambda: _FakeSettings())
    monkeypatch.setattr("quorum_backend.core.gemini_quota._redis_command", _fake_redis_command)

    await reserve_gemini_quota_slot(model="any-model-irrelevant-here", daily_limit=20)

    assert all(call[0] != "DECR" for call in calls)


async def test_reserve_gemini_quota_slot_sets_a_real_expiry_only_on_the_real_key_creating_call(monkeypatch):
    class _FakeSettings:
        upstash_redis_url = "https://real-looking.example.invalid"
        upstash_redis_rest_token = "fake-token-never-sent-anywhere-real"

    calls: list[tuple[str, ...]] = []

    async def _fake_redis_command(*parts, **_kwargs):
        calls.append(parts)
        if parts[0] == "INCR":
            return 1  # a real, freshly-created key
        return 1

    monkeypatch.setattr("quorum_backend.core.gemini_quota.get_settings", lambda: _FakeSettings())
    monkeypatch.setattr("quorum_backend.core.gemini_quota._redis_command", _fake_redis_command)

    await reserve_gemini_quota_slot(model="any-model-irrelevant-here", daily_limit=20)

    assert [call[0] for call in calls] == ["INCR", "EXPIRE"]


# --- Real, live Upstash Redis tests (skipped without real credentials) ---

_TEST_MODEL_PREFIX = "test-quota-model-never-a-real-gemini-model"


def _unique_test_model() -> str:
    # A real, distinct model name per test -- guarantees each test's
    # own real Redis key is fresh (never collides with a prior test
    # run's own leftover count), without needing a shared fixture to
    # coordinate cleanup ordering.
    return f"{_TEST_MODEL_PREFIX}-{uuid.uuid4()}"


async def _delete_real_test_key(model: str) -> None:
    settings = get_settings()
    key = f"gemini:generate_content:{model}:{_today_google_reset_date_string()}"
    await _redis_command("DEL", key, base_url=settings.upstash_redis_url, token=settings.upstash_redis_rest_token)


@pytest.mark.skipif(not _HAS_REAL_REDIS, reason="no real UPSTASH_REDIS_URL/UPSTASH_REDIS_REST_TOKEN configured in this environment")
async def test_reserve_gemini_quota_slot_succeeds_for_a_real_fresh_key():
    model = _unique_test_model()
    try:
        await reserve_gemini_quota_slot(model=model, daily_limit=20)
    finally:
        await _delete_real_test_key(model)


@pytest.mark.skipif(not _HAS_REAL_REDIS, reason="no real UPSTASH_REDIS_URL/UPSTASH_REDIS_REST_TOKEN configured in this environment")
async def test_reserve_gemini_quota_slot_allows_exactly_the_real_configured_daily_limit():
    model = _unique_test_model()
    try:
        for _ in range(3):
            await reserve_gemini_quota_slot(model=model, daily_limit=3)
        # The 4th real reservation against a real limit of 3 must be
        # the one that raises -- not the 3rd, and not silently allowed.
        with pytest.raises(GeminiQuotaExhaustedError):
            await reserve_gemini_quota_slot(model=model, daily_limit=3)
    finally:
        await _delete_real_test_key(model)


@pytest.mark.skipif(not _HAS_REAL_REDIS, reason="no real UPSTASH_REDIS_URL/UPSTASH_REDIS_REST_TOKEN configured in this environment")
async def test_reserve_gemini_quota_slot_settles_at_the_real_limit_not_runs_away(monkeypatch):
    """Real, live regression test for the real DECR-on-reject fix this
    module's own CRITICAL-tier review found: a rejected reservation
    previously kept incrementing the real counter forever with nothing
    to give the slot back, live-confirmed to run away to 31 against a
    real limit of 20. Several real, rejected attempts in a row must
    settle the real counter at exactly `daily_limit`, never climb
    past it."""
    model = _unique_test_model()
    settings = get_settings()
    key = f"gemini:generate_content:{model}:{_today_google_reset_date_string()}"
    try:
        await reserve_gemini_quota_slot(model=model, daily_limit=2)
        await reserve_gemini_quota_slot(model=model, daily_limit=2)
        for _ in range(3):
            with pytest.raises(GeminiQuotaExhaustedError):
                await reserve_gemini_quota_slot(model=model, daily_limit=2)

        current = await _redis_command("GET", key, base_url=settings.upstash_redis_url, token=settings.upstash_redis_rest_token)
        assert int(current) == 2  # settled at the real limit, not 5
    finally:
        await _delete_real_test_key(model)


@pytest.mark.skipif(not _HAS_REAL_REDIS, reason="no real UPSTASH_REDIS_URL/UPSTASH_REDIS_REST_TOKEN configured in this environment")
async def test_reserve_gemini_quota_slot_keys_by_model_independently():
    """Real proof two genuinely different models never share a real
    counter -- exhausting one model's real daily budget must never
    block a genuinely different model's own, separate real slot."""
    model_a = _unique_test_model()
    model_b = _unique_test_model()
    try:
        await reserve_gemini_quota_slot(model=model_a, daily_limit=1)
        with pytest.raises(GeminiQuotaExhaustedError):
            await reserve_gemini_quota_slot(model=model_a, daily_limit=1)
        # model_b's own real slot is genuinely unaffected.
        await reserve_gemini_quota_slot(model=model_b, daily_limit=1)
    finally:
        await _delete_real_test_key(model_a)
        await _delete_real_test_key(model_b)


@pytest.mark.skipif(not _HAS_REAL_REDIS, reason="no real UPSTASH_REDIS_URL/UPSTASH_REDIS_REST_TOKEN configured in this environment")
async def test_reserve_gemini_quota_slot_accepts_explicit_redis_credential_overrides():
    """Real, live proof the optional `redis_url`/`redis_token`
    parameters genuinely work, not just accepted and ignored -- passes
    the real, live Upstash credentials explicitly rather than letting
    the function fall back to `get_settings()`, closing the real,
    disclosed testability gap this module's own CRITICAL-tier review
    found (no seam existed to test the real enforcement logic against
    a real target without relying on ambient environment config)."""
    settings = get_settings()
    model = _unique_test_model()
    try:
        await reserve_gemini_quota_slot(
            model=model, daily_limit=1, redis_url=settings.upstash_redis_url, redis_token=settings.upstash_redis_rest_token,
        )
        with pytest.raises(GeminiQuotaExhaustedError):
            await reserve_gemini_quota_slot(
                model=model, daily_limit=1, redis_url=settings.upstash_redis_url, redis_token=settings.upstash_redis_rest_token,
            )
    finally:
        await _delete_real_test_key(model)


@pytest.mark.skipif(not _HAS_REAL_REDIS, reason="no real UPSTASH_REDIS_URL/UPSTASH_REDIS_REST_TOKEN configured in this environment")
async def test_redis_command_incr_returns_the_real_incremented_count():
    model = _unique_test_model()
    settings = get_settings()
    key = f"gemini:generate_content:{model}:{_today_google_reset_date_string()}"
    try:
        first = await _redis_command("INCR", key, base_url=settings.upstash_redis_url, token=settings.upstash_redis_rest_token)
        second = await _redis_command("INCR", key, base_url=settings.upstash_redis_url, token=settings.upstash_redis_rest_token)
        assert first == 1
        assert second == 2
    finally:
        await _redis_command("DEL", key, base_url=settings.upstash_redis_url, token=settings.upstash_redis_rest_token)


@pytest.mark.skipif(not _HAS_REAL_REDIS, reason="no real UPSTASH_REDIS_URL/UPSTASH_REDIS_REST_TOKEN configured in this environment")
async def test_redis_command_raises_on_a_real_invalid_token():
    settings = get_settings()
    with pytest.raises(httpx.HTTPStatusError):
        await _redis_command("INCR", "irrelevant-key", base_url=settings.upstash_redis_url, token="genuinely-not-a-real-token")


@pytest.mark.skipif(not _HAS_REAL_REDIS, reason="no real UPSTASH_REDIS_URL/UPSTASH_REDIS_REST_TOKEN configured in this environment")
async def test_redis_command_percent_encodes_a_real_path_traversal_style_model_name():
    """Real, live regression test for the real, disclosed security fix
    this module's own CRITICAL-tier review found: an unencoded model
    name containing real `../` segments could previously be normalized
    by httpx into an entirely different real Upstash command against
    the same real Bearer token. A real, live round trip with a
    deliberately hostile-shaped key segment must land on the REAL,
    exact key it was given -- never a different, traversed one."""
    hostile_model = "a/../../../SET/attacker-key/1"
    settings = get_settings()
    key = f"gemini:generate_content:{hostile_model}:{_today_google_reset_date_string()}"
    try:
        count = await _redis_command("INCR", key, base_url=settings.upstash_redis_url, token=settings.upstash_redis_rest_token)
        assert count == 1
        # Confirm the real, exact (encoded) key is what actually got
        # written -- not some other, traversed real key.
        stored = await _redis_command("GET", key, base_url=settings.upstash_redis_url, token=settings.upstash_redis_rest_token)
        assert int(stored) == 1
        # And confirm the real attacker-controlled key this traversal
        # would have targeted was never touched.
        attacker_value = await _redis_command(
            "GET", "attacker-key", base_url=settings.upstash_redis_url, token=settings.upstash_redis_rest_token
        )
        assert attacker_value is None
    finally:
        await _redis_command("DEL", key, base_url=settings.upstash_redis_url, token=settings.upstash_redis_rest_token)
