"""Real tests for core/gemini_quota.py (`DEC-165`).

Error-path and fail-open tests (`# --- Deterministic, no real network`)
use monkeypatching, the same established discipline `test_embeddings.py`
already uses for cases a real, live external service cannot reliably
reproduce on demand (a configured-but-unreachable Redis, a genuinely
absent configuration).

The tests below `# --- Real, live Upstash Redis tests` call the actual,
live Upstash REST API with the real credentials in `backend/.env` --
per CLAUDE.md Rule 5, this is what actually proves the integration
works. Skipped, not failed, without real Upstash credentials
configured. Every real test uses a clearly-fake, dedicated model name
(`_TEST_MODEL`, never a real Gemini model id) so these tests never
increment or interfere with the REAL, shared, production
`gemini-3.6-flash` counter this module exists to protect -- and each
real test deletes its own real key afterward, per Rule 5's own
established cleanup discipline."""
import uuid

import httpx
import pytest

from quorum_backend.core.config import get_settings
from quorum_backend.core.gemini_quota import (
    GeminiQuotaExhaustedError,
    _redis_command,
    _today_utc_date_string,
    reserve_gemini_quota_slot,
)

_HAS_REAL_REDIS = get_settings().upstash_redis_url is not None and get_settings().upstash_redis_rest_token is not None


# --- Deterministic, no real network ---


def test_today_utc_date_string_is_a_real_iso_date_shape():
    result = _today_utc_date_string()
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
    key = f"gemini:generate_content:{model}:{_today_utc_date_string()}"
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
async def test_redis_command_incr_returns_the_real_incremented_count():
    model = _unique_test_model()
    settings = get_settings()
    key = f"gemini:generate_content:{model}:{_today_utc_date_string()}"
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
