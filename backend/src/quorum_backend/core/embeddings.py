"""Real, live Gemini embedding calls -- the backend's first real,
production-code call to an external LLM-family API, not a one-off
verification script. `DEC-098` live-tested `GEMINI_API_KEY`'s validity;
nothing in `backend/src` has ever actually called Gemini until this
module (`orchestration.py`'s own Stage B calls are, and remain, an
injected `Callable`/`Awaitable` dependency -- confirmed by direct
search before writing this file -- so there was no existing in-repo
pattern for a real outbound Gemini call to follow; this module is that
pattern's first real instance).

A real, disclosed deviation from `QUORUM_MASTER_REFERENCE.md` §5's
locked embedding-model choice (Qwen3-Embedding-0.6B), decided by
Preethish directly rather than silently substituted: that model is
never wired anywhere in this backend, and its intended runtime
(on-device vs. server-side) is never specified -- running a real
~0.6B-parameter model on serverless, scale-to-zero, free-tier Cloud
Run would be a genuine cold-start/resource risk this project's own
confirmed constraints don't accommodate, and `note_embeddings` already
stores each item's raw `content` in Postgres directly, so on-device
generation would buy no real privacy benefit here either. Gemini's own
embedding API is used instead: a real, already-provisioned credential
(`DEC-098`), no new external signup, fits this deployment's serverless
shape cleanly. Logged as a real, disclosed open item (`STATUS_INDEX.md`),
not a silent spec rewrite.

The real model name (`gemini-embedding-001`) and its real, live output
dimension (3072) were both confirmed directly against the actual
Gemini API before writing this file or any migration touching
`note_embeddings.embedding`'s column type -- `text-embedding-004`
(the model this session first assumed, matching a commonly-cited
Gemini embedding model name) returned a real, live 404 for this
project's real API key/version, confirmed by a real call, not assumed
correct from memory. `ListModels` was then used to find the real,
currently-available embedding models for this key, and a real
`embedContent` call against `gemini-embedding-001` confirmed the real
3072-dimension default output -- matching `QUORUM_MASTER_REFERENCE.md`
§5's own explicit caution never to hardcode a guessed dimension.
"""
from __future__ import annotations

import httpx

GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"

# Real, live-confirmed default output size for this model -- see this
# file's own docstring for how this was verified, not assumed.
GEMINI_EMBEDDING_DIMENSION = 3072

_EMBED_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_EMBEDDING_MODEL}:embedContent"


class EmbeddingError(Exception):
    """Raised on any failure to obtain a real embedding -- a network
    failure, a non-200 response, a malformed body, or an unexpected
    output dimension. Never silently substituted with a zero vector or
    an empty result, either of which would corrupt search results
    without any visible signal that anything actually went wrong."""


async def embed_text(text: str, *, api_key: str) -> list[float]:
    """Real, live call to Gemini's `embedContent` endpoint. Raises
    `EmbeddingError` on any failure -- callers (`features/search.py`)
    are expected to let this propagate into a real, honest HTTP error,
    never to catch-and-substitute a fake vector."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                _EMBED_URL,
                params={"key": api_key},
                json={"content": {"parts": [{"text": text}]}},
            )
        except httpx.HTTPError as exc:
            raise EmbeddingError(f"Gemini embedding request failed: {exc}") from exc

    if response.status_code != 200:
        raise EmbeddingError(f"Gemini embedding API returned {response.status_code}: {response.text}")

    try:
        data = response.json()
        values = data["embedding"]["values"]
    except (ValueError, KeyError, TypeError) as exc:
        raise EmbeddingError(f"Gemini embedding response was malformed: {exc}") from exc

    if len(values) != GEMINI_EMBEDDING_DIMENSION:
        raise EmbeddingError(
            f"Gemini returned a {len(values)}-dimension vector, expected {GEMINI_EMBEDDING_DIMENSION} "
            "-- the model's real output shape may have changed since this was last confirmed live."
        )

    return values
