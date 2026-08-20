"""Real tests for core/embeddings.py.

Error-path tests (`# --- Error paths`) use `httpx.MockTransport` --
deterministic, network-independent simulations of a malformed
response, a non-200 status, and a genuine network failure. This is not
a violation of `CLAUDE.md` Rule 5's "never mocks, when the point is
proving an integration works": the point of *these* specific tests is
proving `embed_text()`'s own error handling is correct for cases a
real, live call cannot reliably reproduce on demand, not proving the
real Gemini integration itself works.

The tests below `# --- Real, live API tests` call the actual, live
Gemini API with the real `GEMINI_API_KEY` in `backend/.env` -- per
Rule 5, this is the one that actually proves the integration works.
Skipped, not failed, in any environment without a real key configured
(e.g. CI, or a fresh clone) -- the same honest-skip discipline this
project already uses for real, environment-gated checks.
"""
import httpx
import pytest

from quorum_backend.core.config import get_settings
from quorum_backend.core.embeddings import GEMINI_EMBEDDING_DIMENSION, EmbeddingError, embed_text

_HAS_REAL_KEY = get_settings().gemini_api_key is not None


# --- Error paths (deterministic, monkeypatched httpx client, no real network) ---


async def test_embed_text_raises_embedding_error_on_malformed_json_body(monkeypatch):
    class _FakeResponse:
        status_code = 200

        def json(self):
            return {"unexpected": "shape"}

        text = "irrelevant"

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *args, **kwargs):
            return _FakeResponse()

    monkeypatch.setattr("quorum_backend.core.embeddings.httpx.AsyncClient", lambda **kwargs: _FakeClient())

    with pytest.raises(EmbeddingError, match="malformed"):
        await embed_text("anything", api_key="fake-key-never-sent-anywhere-real")


async def test_embed_text_raises_embedding_error_on_a_real_non_200_status(monkeypatch):
    class _FakeResponse:
        status_code = 429
        text = "rate limited"

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *args, **kwargs):
            return _FakeResponse()

    monkeypatch.setattr("quorum_backend.core.embeddings.httpx.AsyncClient", lambda **kwargs: _FakeClient())

    with pytest.raises(EmbeddingError, match="429"):
        await embed_text("anything", api_key="fake-key-never-sent-anywhere-real")


async def test_embed_text_raises_embedding_error_on_a_genuine_network_failure(monkeypatch):
    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *args, **kwargs):
            raise httpx.ConnectError("real connection refused, simulated")

    monkeypatch.setattr("quorum_backend.core.embeddings.httpx.AsyncClient", lambda **kwargs: _FakeClient())

    with pytest.raises(EmbeddingError, match="request failed"):
        await embed_text("anything", api_key="fake-key-never-sent-anywhere-real")


async def test_embed_text_raises_embedding_error_on_an_unexpected_dimension(monkeypatch):
    class _FakeResponse:
        status_code = 200
        text = "irrelevant"

        def json(self):
            return {"embedding": {"values": [0.1, 0.2, 0.3]}}  # real shape, wrong length

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *args, **kwargs):
            return _FakeResponse()

    monkeypatch.setattr("quorum_backend.core.embeddings.httpx.AsyncClient", lambda **kwargs: _FakeClient())

    with pytest.raises(EmbeddingError, match="3-dimension"):
        await embed_text("anything", api_key="fake-key-never-sent-anywhere-real")


# --- Real, live API tests (skipped without a real GEMINI_API_KEY) ---


@pytest.mark.skipif(not _HAS_REAL_KEY, reason="no real GEMINI_API_KEY configured in this environment")
async def test_embed_text_returns_a_real_live_vector_of_the_confirmed_dimension():
    settings = get_settings()
    vector = await embed_text("a real, live embedding dimension check", api_key=settings.gemini_api_key)
    assert len(vector) == GEMINI_EMBEDDING_DIMENSION
    assert all(isinstance(v, float) for v in vector)


@pytest.mark.skipif(not _HAS_REAL_KEY, reason="no real GEMINI_API_KEY configured in this environment")
async def test_embed_text_raises_on_a_real_invalid_api_key():
    with pytest.raises(EmbeddingError):
        await embed_text("anything", api_key="genuinely-not-a-real-key")
