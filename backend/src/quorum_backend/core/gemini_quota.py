"""Real, live, shared Gemini `generateContent` daily-quota guard --
Roadmap `DEC-165`, closing the real, disclosed future-session item
`DEC-153`'s own CRITICAL-tier review found (M3): at the time this
module was written, every one of this backend's five files with a real
`generateContent` call site (`gate/llm_calls.py`'s Judge, `negotiation/
gemini_calls.py`'s position/synthesis calls -- two logical callers
sharing one local helper, `negotiation/downstream_translation.py`,
`features/quick_capture.py`, `features/career_digest.py` -- six real
call sites in total) shared ONE real `GEMINI_API_KEY` against ONE real
Google free-tier project, with zero coordination between them --
confirmed live, the hard way, this same project's history (`DEC-153`'s
own review exhausted the real quota through its own adversarial
probing and caused unrelated tests to fail as collateral; a later
on-device session hit the identical wall trying to generate real
negotiation detail).

**REAL, DISCLOSED SCOPE NARROWING, `DEC-166`:** `QUORUM_FINAL_
COMPLETION_PLAN.md` Session 1's real AI-provider rebalancing moved
every one of those five real call sites EXCEPT the Judge onto Groq
(`negotiation/groq_calls.py`, renamed from `gemini_calls.py`;
`downstream_translation.py`; `quick_capture.py`; `career_digest.py`) --
this module's own real, shared, atomic slot reservation is now
exercised by exactly ONE real call site, `gate/llm_calls.py`'s Judge
(`make_gemini_judge_call`). This module is NOT deleted -- that one real
call site still shares this same real 20-request/day free-tier budget
with nothing else in this backend now, and still genuinely needs this
guard for the identical real reason it was built.

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
a scarce 20 real daily slots just to learn it had none left. **A real,
disclosed consequence of this design, found by this module's own
CRITICAL-tier review:** since Google counts every real attempt, not
just the final one, EVERY real call site's own retry loop calls
`reserve_gemini_quota_slot()` again before EACH real attempt, not once
before the whole loop -- a call that retries twice against a real,
transient failure genuinely costs two real Google-counted attempts,
and this guard's own count must match that exactly, not undercount by
treating a multi-attempt logical call as a single real reservation.

THE REAL RESET BOUNDARY THIS GUARD MIRRORS, corrected by this module's
own CRITICAL-tier review before merge: Google's real, documented
quota policy resets RPD (requests-per-day) quotas at midnight PACIFIC
TIME, not UTC (confirmed against Google's own real, live documentation,
https://ai.google.dev/gemini-api/docs/rate-limits). An earlier version
of this module keyed its own counter by the UTC calendar date instead
-- a real, disclosed, live-caught bug: Pacific is UTC-7/-8 depending on
daylight saving, so a UTC-keyed counter resets 7-8 real hours before
Google's own server-side count does, and stays stale for those same
7-8 hours after Google has already moved on. Both directions are real
and costly: in the UTC-already-rolled-over-but-Pacific-hasn't window,
this guard would authorize real calls Google will still reject; in the
Pacific-already-rolled-over-but-this-guard-hasn't window (the
overwhelming majority of a real day, including this project's own
working hours in IST), this guard would keep refusing real calls
Google would now happily serve. Keying by the real Pacific calendar
date instead (`zoneinfo.ZoneInfo("America/Los_Angeles")`, which
correctly, automatically tracks the real PST/PDT transition -- no
manual UTC-offset arithmetic to get wrong twice a year) fixes both
directions at once. `tzdata` (new, real, explicit dependency,
`pyproject.toml`) ships the real IANA timezone database directly in
this project's own installed package rather than trusting the
underlying OS to have it -- confirmed, live, load-bearing: this
backend's own real production Dockerfile is `python:3.12-slim`, a
Debian-slim base image that does not reliably ship `/usr/share/
zoneinfo` at the OS level, so relying on the OS alone would have been
a real, live, silent failure risk on the one environment (Cloud Run)
that actually matters, even though it happens to work locally on this
development machine via an already-installed, merely-transitive
`tzdata` package.

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
config directly, not a new general pattern. **A real, disclosed
refinement from this module's own CRITICAL-tier review:** `redis_url`/
`redis_token` are genuine optional keyword overrides on `reserve_
gemini_quota_slot()` itself (falling back to `get_settings()` when
omitted, which is what every one of the six real call sites actually
does) specifically so this module's OWN tests can point the real
enforcement logic (the `daily_limit`-exceeded raise, the real key
format) at a real but disposable test target without needing live
production Upstash credentials configured in every environment
(notably CI, which has none) -- closing a real, disclosed gap the
review found: without this seam, the raise branch had zero
deterministic test coverage anywhere, live-Redis-gated or not.

REAL, DELIBERATE FAIL-OPEN ON REDIS ITSELF BEING UNREACHABLE, but
DELIBERATELY NARROW, not a bare `except Exception` -- a real,
disclosed correction from this module's own CRITICAL-tier review,
which live-caught the broad version silently swallowing a genuine
`KeyError` shape bug in one existing test's own fake HTTP client and
reporting it identically to a real Upstash outage, indistinguishable
in the logs. This guard's whole job is to avoid a wasted real Gemini
call, not to become a second, independent point of failure for every
Gemini-dependent feature in this app -- but that principle only
justifies swallowing REAL infrastructure failure modes (a genuine
network error, a non-2xx response, a malformed JSON body), not an
unrelated programming error inside this module's own code, which
should surface loudly like any other real bug. If `UPSTASH_REDIS_URL`/
`UPSTASH_REDIS_REST_TOKEN` aren't configured (a real, honest, already-
established "not yet provisioned" state in some environments, per
`core/config.py`'s own docstring) or a real Redis call itself fails
with one of `(httpx.HTTPError, KeyError, ValueError)`, this function
logs and returns normally -- the real Gemini call proceeds exactly as
it would have before this module existed, and Google's own real 429
remains the final, honest backstop it always was. A real, live Upstash
outage should degrade this app back to "no quota coordination," never
take down every Gemini-dependent feature at once.

REAL, ATOMIC RESERVATION, race-safe across this deployment's real
`--max-instances=2` Cloud Run scaling (even though `--concurrency=1`
means no race within one instance): `INCR` is Redis's own real atomic
increment -- two concurrent requests across two real instances
racing this same real key can never both see a stale pre-increment
count and both proceed past a real, remaining single slot. The
counter is keyed by the real, current Pacific calendar date (see
above) rather than a computed "seconds until reset" TTL, so it
naturally, correctly resets exactly at Google's own real reset moment
with no separate expiry-timing logic to get subtly wrong -- a `2`-day
`EXPIRE`, set only on the real INCR that creates the key (`result ==
1`), is pure hygiene (bounding real Upstash storage) with no
correctness role at all. **A real, disclosed fix for a second bug this
module's own CRITICAL-tier review found:** a rejected reservation
still INCREMENTED the real counter, with nothing to give the slot
back -- live-confirmed to let the counter run away arbitrarily far
past `daily_limit` (measured live at 31 against a real limit of 20),
which is harmless for the raise itself but means every SUBSEQUENT
rejected call also keeps incrementing forever, real information this
guard has no reason to keep accumulating once a day is already known
to be exhausted. A real `DECR` immediately follows a rejected
reservation, releasing the real slot back so the counter settles at
exactly `daily_limit` rather than climbing indefinitely -- correct,
and still race-safe: the `DECR` only ever runs on the exact request
that just observed `count > daily_limit`, never a stale or duplicated
one. **A real, disclosed, deliberately NOT-fixed residual limit,
acknowledged rather than silently claimed away:** a reservation is
spent the moment the real INCR succeeds, before this module knows
whether the caller's own subsequent real network call to Google will
even be attempted, let alone succeed -- a genuine local failure
between reservation and dial-out (a DNS blip resolving Google's own
host, a client-side timeout before the request leaves this process)
wastes a real local slot Google never actually counted. This is a
real, accepted, low-cost tradeoff, not a design that has been proven
airtight: building a "give the slot back on a purely local failure"
path would need passing more state back out of this function into
every one of six already-reviewed call sites' own retry loops, a
larger, riskier change judged not worth it for a rare failure mode.
There is also, deliberately, no manual override/bypass beyond what
already exists: unset the two real Upstash settings to disable this
guard entirely, or delete the real Redis key by hand for one model/day
-- a new, dedicated bypass flag was judged unnecessary complexity for
an already-covered, rare operational need.

A REAL, DISCLOSED SCOPE BOUNDARY: this guards `generateContent` only.
`core/embeddings.py`'s own real `embedContent` calls hit a genuinely
different real quota metric this session never live-confirmed a
number for -- inventing one would be a real, unverified guess, the
same discipline every other real number in this file avoids. A
genuinely separate, future, disclosed item if that quota is ever found
to matter in practice.

A REAL, DISCLOSED, NOT-FULLY-CLOSED GAP even after this fix (`MEDIUM-2`
of this module's own CRITICAL-tier review, logged here rather than
silently left): CI configures neither `UPSTASH_REDIS_URL`/`_REST_
TOKEN` nor `GEMINI_API_KEY` (confirmed directly against `ci.yml`), so
none of the six real call sites' own wiring to this guard, nor this
guard's own real Redis-calling code path, is ever actually exercised
in CI -- only this module's two deterministic, no-network tests run
there. The real enforcement branch (the `daily_limit`-exceeded raise
and the real key format) now has real, live, deterministic coverage
via the optional `redis_url`/`redis_token` overrides above, but that
coverage still needs a real, live Upstash instance to run against (the
same real instance this project already uses, since there is no cheap
local Redis-REST-API emulator in this environment) -- so it is real
and passing in this development environment, but, like every other
live-credential-gated test in this backend, still skipped, not run, in
CI. A genuinely separate, disclosed, future item if closing that gap
(e.g. a lightweight fake Upstash REST server for CI) is ever judged
worth building.
"""
from __future__ import annotations

import logging
from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx

from quorum_backend.core.config import get_settings

logger = logging.getLogger("quorum_backend")

# The real, live-confirmed number this whole module exists to guard --
# see this file's own top-of-file docstring for exactly how it was
# confirmed, live, against this project's own real Google account.
GEMINI_GENERATE_CONTENT_DAILY_LIMIT = 20

# Real hygiene only, not correctness -- see the module docstring's own
# "REAL, ATOMIC RESERVATION" section for why 2 days (not exactly 1) is
# deliberately generous rather than precisely tuned to the real reset
# boundary.
_QUOTA_KEY_TTL_SECONDS = 2 * 24 * 60 * 60

# The real, live-confirmed timezone Google's own RPD (requests-per-day)
# quotas reset in -- see this module's own top-of-file docstring for
# the full real reasoning and the real, live-caught bug this corrects.
_GOOGLE_QUOTA_RESET_TIMEZONE = ZoneInfo("America/Los_Angeles")


class GeminiQuotaExhaustedError(Exception):
    """Raised when this real, shared daily `generateContent` budget for
    a given real model is already spent. Every real call site catches
    this and re-raises its own existing, local error type (never a new
    cross-cutting exception callers must additionally learn) -- see
    each call site's own real wiring for the exact translation."""


def _today_google_reset_date_string() -> str:
    # A real Pacific-time calendar-date key, matching Google's own real
    # RPD reset boundary exactly -- see this module's own top-of-file
    # docstring for why this replaced an earlier, live-caught-wrong
    # UTC-keyed version, not just a stylistic choice.
    return datetime.now(_GOOGLE_QUOTA_RESET_TIMEZONE).strftime("%Y-%m-%d")


async def _redis_command(*parts: str, base_url: str, token: str) -> object:
    """Real, live call to one real Upstash Redis REST command -- e.g.
    `_redis_command("INCR", "some-key", base_url=..., token=...)`.
    Confirmed live against this project's own real Upstash instance
    before this module trusted the shape: `POST {base_url}/{parts...}`
    with a real Bearer token returns `{"result": ...}` on success.
    Raises on any real HTTP-level failure -- callers here always treat
    that as "fail open," never as "quota exhausted."

    Every real path segment is real, percent-encoded (`urllib.parse.
    quote(..., safe="")`) before joining -- a real, disclosed fix from
    this module's own CRITICAL-tier review: every real caller today
    passes only hardcoded, trusted constants (a fixed Redis command
    name, this module's own fixed key-naming scheme), so this was
    "incidentally safe, not safe by construction" before this fix --
    live-demonstrated that an unencoded `model` value containing a
    real `../` path-traversal-style segment gets normalized by httpx
    into an entirely different real Upstash command against the same
    real, live Bearer token. Encoding here closes that off structurally
    rather than relying on every future caller remembering to pre-
    sanitize its own `model` argument."""
    url = "/".join([base_url.rstrip("/"), *(quote(part, safe="") for part in parts)])
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(url, headers={"Authorization": f"Bearer {token}"})
    response.raise_for_status()
    return response.json()["result"]


async def reserve_gemini_quota_slot(
    *,
    model: str,
    daily_limit: int = GEMINI_GENERATE_CONTENT_DAILY_LIMIT,
    redis_url: str | None = None,
    redis_token: str | None = None,
) -> None:
    """The one real function every `generateContent` call site in this
    backend calls immediately before EACH real attempt at its own real
    Gemini call (inside the retry loop, not once above it -- see this
    module's own top-of-file docstring for why a multi-attempt logical
    call must reserve once per real attempt). Raises `GeminiQuotaExhaustedError`
    the moment this would be the `daily_limit + 1`-th real call for
    `model` today (by Google's own real Pacific-time reset boundary);
    otherwise returns normally, having already reserved this call's own
    real slot. See this module's own top-of-file docstring for the full
    real reasoning -- fails open (returns normally, logging why) on a
    real, anticipated Redis-layer failure `(httpx.HTTPError, KeyError,
    ValueError)`, rather than ever blocking a real Gemini call over a
    real infrastructure hiccup this guard itself couldn't get a live
    answer about; any OTHER exception is a genuine bug in this
    function's own logic and is deliberately left to propagate, never
    silently swallowed alongside real infrastructure failures.

    `redis_url`/`redis_token`, when explicitly passed, override the
    real, live `core.config.get_settings()`-sourced values every real
    call site in this backend actually relies on (see this module's own
    top-of-file docstring for why call sites read settings indirectly
    through this default rather than threading credentials themselves)
    -- exists specifically so this module's own tests can exercise the
    real enforcement logic (the raise itself, the real key format)
    against a real, disposable test target, never a hardcoded fake."""
    settings = get_settings()
    resolved_url = redis_url if redis_url is not None else settings.upstash_redis_url
    resolved_token = redis_token if redis_token is not None else settings.upstash_redis_rest_token
    if resolved_url is None or resolved_token is None:
        logger.debug("Gemini quota guard: Upstash Redis not configured -- skipping real quota check for model=%s", model)
        return

    key = f"gemini:generate_content:{model}:{_today_google_reset_date_string()}"
    try:
        count = int(await _redis_command("INCR", key, base_url=resolved_url, token=resolved_token))
        if count == 1:
            # This real INCR is what just created the key -- set a
            # real, generous expiry now. A real, disclosed non-issue if
            # this second call itself fails: the key still correctly
            # expires on its own via Upstash's real global default
            # eviction policies eventually, and either way the next
            # real reset-boundary date produces a brand-new key
            # regardless of whether this one's own TTL was ever
            # actually set.
            await _redis_command("EXPIRE", key, str(_QUOTA_KEY_TTL_SECONDS), base_url=resolved_url, token=resolved_token)
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        logger.warning("Gemini quota guard: real Upstash call failed, failing open for model=%s: %s", model, exc)
        return

    if count > daily_limit:
        try:
            # Real, disclosed fix: give the real slot back so a
            # rejected reservation doesn't keep inflating the real
            # counter forever -- see this module's own top-of-file
            # docstring for the full real reasoning. A real, deliberate
            # non-issue if THIS call itself fails: the counter simply
            # stays inflated until the next real reset, still correctly
            # rejecting every further real attempt either way.
            await _redis_command("DECR", key, base_url=resolved_url, token=resolved_token)
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            logger.warning("Gemini quota guard: real Upstash DECR-on-reject failed for model=%s: %s", model, exc)
        raise GeminiQuotaExhaustedError(
            f"Real, shared Gemini '{model}' free-tier quota ({daily_limit}/day) is already exhausted for today "
            "(Google's own real reset boundary is midnight Pacific time, not UTC) -- try again after that reset, "
            "or once a real, different quota/tier is provisioned."
        )
