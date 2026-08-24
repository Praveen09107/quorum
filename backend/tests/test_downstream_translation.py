"""Real tests for negotiation/downstream_translation.py (DEC-127).

Error-path tests use a monkeypatched httpx client, matching every other
real Gemini-backed call site's own established pattern in this backend.
The tests below `# --- Real, live tests` call the actual, live Gemini
API. Skipped, not failed, without a real GEMINI_API_KEY configured.
"""
import httpx
import pytest

from quorum_backend.core.config import get_settings
from quorum_backend.negotiation.downstream_translation import (
    DownstreamTranslationError,
    make_gemini_downstream_translation_call,
)

_settings = get_settings()
_HAS_GEMINI_KEY = _settings.gemini_api_key is not None


class _FakeResponse:
    def __init__(self, status_code: int, json_body: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json_body = json_body
        self.text = text

    def json(self):
        return self._json_body


# --- Deterministic (monkeypatched httpx client, no real network) ---


async def test_translation_call_raises_for_a_domain_with_no_real_schema(monkeypatch):
    translation_call = make_gemini_downstream_translation_call(api_key="fake-key")
    with pytest.raises(DownstreamTranslationError):
        await translation_call("career", "Any description -- career is never a real negotiation domain")


async def test_translation_call_raises_after_real_retries_exhausted(monkeypatch):
    call_count = 0

    async def fake_post(self, url, headers=None, json=None):
        nonlocal call_count
        call_count += 1
        return _FakeResponse(503, text="overloaded")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    translation_call = make_gemini_downstream_translation_call(api_key="fake-key")
    with pytest.raises(DownstreamTranslationError):
        await translation_call("finance", "Cut discretionary spending by 2000 this month")
    assert call_count == 2


async def test_translation_call_returns_the_real_parsed_json_for_finance(monkeypatch):
    async def fake_post(self, url, headers=None, json=None):
        body = '{"action": "update_budget", "amount": 2000, "category": "discretionary", "payee": null}'
        return _FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": body}]}}]})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    translation_call = make_gemini_downstream_translation_call(api_key="fake-key")
    result = await translation_call("finance", "Cut discretionary spending by 2000 this month")
    assert result == {"action": "update_budget", "amount": 2000, "category": "discretionary", "payee": None}


async def test_translation_call_returns_the_real_parsed_json_for_tasks(monkeypatch):
    async def fake_post(self, url, headers=None, json=None):
        body = '{"title": "Follow up on report", "estimated_hours": 2.0, "deadline_iso": "2026-09-01T09:00:00+00:00"}'
        return _FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": body}]}}]})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    translation_call = make_gemini_downstream_translation_call(api_key="fake-key")
    result = await translation_call("tasks", "Add a real follow-up task for the report")
    assert result["title"] == "Follow up on report"
    assert result["estimated_hours"] == 2.0


async def test_translation_call_returns_the_real_parsed_json_for_calendar(monkeypatch):
    async def fake_post(self, url, headers=None, json=None):
        body = '{"title": "Reschedule check-in", "start_iso": "2026-09-01T09:00:00+00:00", "end_iso": "2026-09-01T09:30:00+00:00"}'
        return _FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": body}]}}]})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    translation_call = make_gemini_downstream_translation_call(api_key="fake-key")
    result = await translation_call("calendar", "Move the recurring check-in to a shorter slot")
    assert result["title"] == "Reschedule check-in"


# --- Real, live tests (skipped without a real GEMINI_API_KEY configured) ---


@pytest.mark.skipif(not _HAS_GEMINI_KEY, reason="no real GEMINI_API_KEY configured in this environment")
async def test_real_live_translation_call_produces_a_real_finance_shape():
    translation_call = make_gemini_downstream_translation_call(api_key=_settings.gemini_api_key)
    result = await translation_call(
        "finance", "Reduce the dining-out budget by roughly 1500 for the rest of the month to free up room for a real task deadline."
    )
    assert result["action"] in ("log_expense", "update_budget")
    assert isinstance(result["amount"], (int, float))
    assert result["amount"] > 0
    assert isinstance(result["category"], str) and result["category"]


@pytest.mark.skipif(not _HAS_GEMINI_KEY, reason="no real GEMINI_API_KEY configured in this environment")
async def test_real_live_translation_call_produces_a_real_tasks_shape():
    translation_call = make_gemini_downstream_translation_call(api_key=_settings.gemini_api_key)
    result = await translation_call(
        "tasks", "Add a real task to follow up on the quarterly report by next Friday, roughly 3 hours of work."
    )
    assert isinstance(result["title"], str) and result["title"]
    assert isinstance(result["estimated_hours"], (int, float))
    assert result["estimated_hours"] > 0
