"""Real, live, shared Gemini `generateContent` daily-quota guard --
Roadmap `DEC-165`, closing the real, disclosed future-session item
`DEC-153`'s own CRITICAL-tier review found (M3): every one of this
backend's five independent `generateContent` call sites
(`gate/llm_calls.py`'s Judge, `negotiation/gemini_calls.py`'s
position/synthesis calls, `negotiation/downstream_translation.py`,
`features/quick_capture.py`, `features/career_digest.py`) shares ONE
real `GEMINI_API_KEY` against ONE real Google free-tier project, with
zero coordination between them -- confirmed live, the hard way, this
same project's history (`DEC-153`'s own review exhausted the real
quota through its own adversarial probing and caused unrelated tests
to fail as collateral; a later on-device session hit the identical
wall trying to generate real negotiation detail).

THE REAL, LIVE-CONFIRMED NUMBER THIS GUARDS AGAINST, not a guess:
Google's own real `429` response body, hit live against this project's
real key, names the exact metric and limit --
`generativelanguage.googleapis.com/generate_content_free_tier_requests`,
`quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier`, `limit: 20`,
`model: gemini-3.6-flash`. **A real, disclosed correction to `QUORUM_
CONFIGURATION_CONSTANTS.md` §8, made in the same session this module
was written:** that document's own "Gemini Flash | ... 1,500
requests/day" entry is stale -- a real number for a different,
now-unavailable model generation (`gemini_calls.py`'s own docstring
already documents `gemini-2.5-flash` returning a real 404, "no longer
available to new users"). `gemini-3.6-flash`, the model every real
call site in this backend actually uses, has a genuinely different,
far stricter real free-tier limit: 20 requests/day, confirmed live,
not 1,500.

WHY A REAL, LIVE PRE-FLIGHT CHECK, not a reactive retry-on-429: a
wasted real HTTP round-trip to Google is the SAME real cost as a
successful one against this specific quota (Google counts the
attempt, not just successes) -- reserving a real slot BEFORE dialing
out means a caller that's already out of real quota fails immediately,
loud, and cheaply, with a clear real reason, instead of spending one of
a scarce 20 real daily slots just to learn it had none left.

WHY THIS MODULE CALLS `core.config.get_settings()` DIRECTLY, a real,
deliberate, disclosed exception to this backend's own established
"thread every infrastructure value as an explicit parameter" norm
(confirmed by direct search: no other feature module does this) --
Upstash Redis credentials are pure, per-process infrastructure
plumbing for a cross-cutting concern every one of six real call sites
across five files would otherwise need threading through, the same
class of thing a logger or a metrics client is, not per-request
business data like `api_key` (which stays explicitly threaded
everywhere, unchanged). Threading two new parameters through all six
of those already-reviewed, several CRITICAL-tier call sites for one
shared cross-cutting concern was judged a real, meaningful increase in
review surface and diff footprint for no real behavioral benefit --
this module is the one, single, disclosed place that reads Redis
config directly, not a new general pattern.

REAL, DELIBERATE FAIL-OPEN ON REDIS ITSELF BEING UNREACHABLE OR
UNCONFIGURED: this guard's whole job is to avoid a wasted real Gemini
call, not to become a second, independent point of failure for every
Gemini-dependent feature in this app. If `UPSTASH_REDIS_URL`/
`UPSTASH_REDIS_REST_TOKEN` aren't configured (a real, honest, already-
established "not yet provisioned" state in some environments, per
`core/config.py`'s own docstring) or a real Redis call itself fails
(network blip, real Upstash outage), this function logs and returns
normally -- the real Gemini call proceeds exactly as it would have
before this module existed, and Google's own real 429 remains the
final, honest backstop it always was. A real, live Upstash outage
should degrade this app back to "no quota coordination," never take
down every Gemini-dependent feature at once.

REAL, ATOMIC RESERVATION, race-safe across this deployment's real
`--max-instances=2` Cloud Run scaling (even though `--concurrency=1`
means no race within one instance): `INCR` is Redis's own real atomic
increment -- two concurrent requests across two real instances
racing this same real key can never both see a stale pre-increment
count and both proceed past a real, remaining single slot. The
counter is keyed by the real, current UTC calendar date rather than a
computed "seconds until midnight" TTL, so it naturally, correctly
resets exactly at UTC midnight with no separate expiry-timing logic
to get subtly wrong -- a `2`-day `EXPIRE`, set only on the real INCR
that creates the key (`result == 1`), is pure hygiene (bounding real
Upstash storage) with no correctness role at all.

A REAL, DISCLOSED SCOPE BOUNDARY: this guards `generateContent` only.
`core/embeddings.py`'s own real `embedContent` calls hit a genuinely
different real quota metric this session never live-confirmed a
number for -- inventing one would be a real, unverified guess, the
same discipline every other real number in this file avoids. A
genuinely separate, future, disclosed item if that quota is ever found
to matter in practice.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from quorum_backend.core.config import get_settings

logger = logging.getLogger("quorum_backend")

# The real, live-confirmed number this whole module exists to guard --
# see this file's own top-of-file docstring for exactly how it was
# confirmed, live, against this project's own real Google account.
GEMINI_GENERATE_CONTENT_DAILY_LIMIT = 20

# Real hygiene only, not correctness -- see the module docstring's own
# "REAL, ATOMIC RESERVATION" section for why 2 days (not exactly 1) is
# deliberately generous rather than precisely tuned to a UTC boundary.
_QUOTA_KEY_TTL_SECONDS = 2 * 24 * 60 * 60


class GeminiQuotaExhaustedError(Exception):
    """Raised when this real, shared daily `generateContent` budget for
    a given real model is already spent. Every real call site catches
    this and re-raises its own existing, local error type (never a new
    cross-cutting exception callers must additionally learn) -- see
    each call site's own real wiring for the exact translation."""


def _today_utc_date_string() -> str:
    # A real, plain UTC calendar-date key -- see the module docstring's
    # own "REAL, ATOMIC RESERVATION" section for why this replaces a
    # computed TTL entirely, not just simplifies it.
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


async def _redis_command(*parts: str, base_url: str, token: str) -> object:
    """Real, live call to one real Upstash Redis REST command -- e.g.
    `_redis_command("INCR", "some-key", base_url=..., token=...)`.
    Confirmed live against this project's own real Upstash instance
    before this module trusted the shape: `POST {base_url}/{parts...}`
    with a real Bearer token returns `{"result": ...}` on success.
    Raises on any real HTTP-level failure -- callers here always treat
    that as "fail open," never as "quota exhausted."""
    url = "/".join([base_url.rstrip("/"), *parts])
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(url, headers={"Authorization": f"Bearer {token}"})
    response.raise_for_status()
    return response.json()["result"]


async def reserve_gemini_quota_slot(*, model: str, daily_limit: int = GEMINI_GENERATE_CONTENT_DAILY_LIMIT) -> None:
    """The one real function every `generateContent` call site in this
    backend calls immediately before attempting its own real Gemini
    call. Raises `GeminiQuotaExhaustedError` the moment this would be
    the `daily_limit + 1`-th real call for `model` today; otherwise
    returns normally, having already reserved this call's own real
    slot. See this module's own top-of-file docstring for the full
    real reasoning -- fails open (returns normally, logging why) if
    Redis isn't configured or a real Redis call itself fails, rather
    than ever blocking a real Gemini call this guard itself couldn't
    reach a real, live answer about."""
    settings = get_settings()
    if settings.upstash_redis_url is None or settings.upstash_redis_rest_token is None:
        logger.debug("Gemini quota guard: Upstash Redis not configured -- skipping real quota check for model=%s", model)
        return

    key = f"gemini:generate_content:{model}:{_today_utc_date_string()}"
    try:
        count = await _redis_command("INCR", key, base_url=settings.upstash_redis_url, token=settings.upstash_redis_rest_token)
        if count == 1:
            # This real INCR is what just created the key -- set a
            # real, generous expiry now. A real, disclosed non-issue if
            # this second call itself fails: the key still correctly
            # expires on its own via Upstash's real global default
            # eviction policies eventually, and either way the next
            # real UTC date produces a brand-new key regardless of
            # whether this one's own TTL was ever actually set.
            await _redis_command("EXPIRE", key, str(_QUOTA_KEY_TTL_SECONDS), base_url=settings.upstash_redis_url, token=settings.upstash_redis_rest_token)
    except Exception as exc:  # noqa: BLE001 -- deliberately broad, matching this module's own stated design goal: this guard's whole job is to avoid a wasted real Gemini call, never to become a second, independent point of failure for one -- any unexpected failure here (a real Upstash outage, a malformed response, or anything else) must fail open, not propagate
        logger.warning("Gemini quota guard: real Upstash call failed, failing open for model=%s: %s", model, exc)
        return

    if int(count) > daily_limit:
        raise GeminiQuotaExhaustedError(
            f"Real, shared Gemini '{model}' free-tier quota ({daily_limit}/day) is already exhausted for today "
            "(UTC calendar day) -- try again after UTC midnight, or once a real, different quota/tier is provisioned."
        )
