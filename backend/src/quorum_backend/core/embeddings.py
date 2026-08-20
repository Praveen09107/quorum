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
shape cleanly. Logged as a real, disclosed open item in
`STATUS_INDEX.md` and `DECISIONS_LOG.md` (`DEC-120`), per Rule 3 --
this module deliberately does not quietly override a "Locked" spec
decision without that record existing.

THE REAL MODEL AND DIMENSION, both confirmed live before any migration
hardcoded either -- `QUORUM_MASTER_REFERENCE.md` §5's own standing
caution is never to hardcode a guessed dimension, and that caution
earned itself twice here:
  1. `text-embedding-004` (this session's first assumption, a commonly-
     cited Gemini embedding model name) returned a real, live 404 for
     this project's real API key and version. `ListModels` was then
     used to find the genuinely-available models.
  2. `gemini-embedding-001`'s real DEFAULT output is 3072 dimensions,
     confirmed by a real `embedContent` call -- and that default is
     unusable for this project: pgvector refuses to build either an
     HNSW or an IVFFlat index above 2000 dimensions, confirmed live
     against the real production database ("column cannot have more
     than 2000 dimensions for hnsw index"). A 3072-dimension column
     would have permanently forced every real search to a sequential
     scan of the user's whole corpus. Found by `DEC-120`'s own
     pre-merge review, before any real row was ever written.

So this module asks for 768 explicitly via `outputDimensionality`
(Gemini's real Matryoshka/MRL truncation, confirmed live returning
exactly 768), which pgvector indexes cleanly with HNSW.

A real, live-confirmed subtlety that follows from that truncation, and
is genuinely easy to miss: the 3072 default comes back already
L2-normalized (measured norm 1.000000), but the MRL-truncated 768
output does NOT (measured norm 0.582911). Cosine distance -- what this
project's real similarity query uses (`<=>`) -- is magnitude-
invariant, so ranking would still be correct either way; the vectors
are re-normalized below anyway, because Google's own guidance for
truncated embeddings says to, because it keeps every stored vector
consistent with the 3072 default's own property, and because it makes
a future switch to an L2-distance operator safe instead of silently
wrong.
"""
from __future__ import annotations

import math

import httpx

GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"

# Real, live-confirmed, and deliberately NOT the model's own 3072
# default -- see this module's docstring for the real pgvector
# 2000-dimension index limit that drives this number.
GEMINI_EMBEDDING_DIMENSION = 768

_EMBED_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_EMBEDDING_MODEL}:embedContent"


class EmbeddingError(Exception):
    """Raised on any failure to obtain a real embedding -- a network
    failure, a non-200 response, a malformed body, or an unexpected
    output dimension. Never silently substituted with a zero vector or
    an empty result, either of which would corrupt search results
    without any visible signal that anything actually went wrong."""


def _l2_normalize(values: list[float]) -> list[float]:
    """Real, explicit L2 normalization -- see this module's docstring
    for why MRL-truncated output genuinely needs it. A zero vector is
    returned unchanged rather than dividing by zero; Gemini has never
    been observed to return one, but a silent NaN vector written into
    `note_embeddings` would be a real, hard-to-trace corruption, and
    pgvector rejects NaN loudly on insert anyway."""
    norm = math.sqrt(sum(v * v for v in values))
    if norm == 0.0:
        return values
    return [v / norm for v in values]


async def embed_text(text: str, *, api_key: str) -> list[float]:
    """Real, live call to Gemini's `embedContent` endpoint. Raises
    `EmbeddingError` on any failure -- callers (`features/search.py`)
    are expected to let this propagate into a real, honest HTTP error,
    never to catch-and-substitute a fake vector.

    The real API key travels in the `x-goog-api-key` HEADER, never as a
    `?key=` query parameter. Both genuinely work (confirmed live), and
    the query-parameter form is the more commonly shown one -- but it
    puts a real, live credential into the request URL, and `httpx` logs
    `request.url` at INFO on its own logger. That log is silent under
    this project's real Dockerfile/uvicorn configuration today, but
    "today" is the whole problem: a single future `logging.basicConfig(
    level=INFO)`, or the Langfuse tracing integration this project
    already has open as real future work, would start writing the real
    key into Cloud Logging with nothing in this file to prevent it. The
    header form has no such failure mode. Found by `DEC-120`'s own
    pre-merge review, which also confirmed the related landmine:
    `httpx.HTTPStatusError`'s own `str()` embeds the full request URL,
    so a future `raise_for_status()` anywhere in this call path would
    have leaked a query-parameter key into an exception message
    directly. There is deliberately no `raise_for_status()` below."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                _EMBED_URL,
                headers={"x-goog-api-key": api_key},
                json={
                    "content": {"parts": [{"text": text}]},
                    "outputDimensionality": GEMINI_EMBEDDING_DIMENSION,
                },
            )
        except httpx.HTTPError as exc:
            # `exc` here is deliberately a transport-level error only
            # (connect/timeout/protocol) -- confirmed live that none of
            # those carry the request URL in their str(), and the key
            # is no longer in the URL regardless.
            raise EmbeddingError(f"Gemini embedding request failed: {type(exc).__name__}: {exc}") from exc

    if response.status_code != 200:
        raise EmbeddingError(f"Gemini embedding API returned {response.status_code}")

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

    return _l2_normalize([float(v) for v in values])
