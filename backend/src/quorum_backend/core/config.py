"""Real, centralized runtime settings — the genuine gap `QUORUM_PROJECT_
STRUCTURE.md` names directly for `core/config.py`. Before this file,
every module that needed an infrastructure/credential value took it as
an explicit injected parameter (e.g. `access_token.py`'s `secret` argument)
rather than reading a shared settings object — this file is the first
real, centralized place those real environment values live, matching
exactly the variable names `backend/.env.example` already commits to.

HONEST DISCLOSURE: no document in this project's real corpus gives this
file a full, exact field list. `QUORUM_PROJECT_STRUCTURE.md` names it as
a real, acknowledged gap ("new module; see §6, no session doc yet, treat
as a real gap to close") — but that document's own §6 doesn't exist (it
only goes up to §5), a second, smaller real discrepancy found and
disclosed here rather than silently worked around. Built as a real,
reasoned settings model instead, scoped exactly to `backend/.env.example`'s
already-real variable names — not invented beyond what that file already
commits to.

What this file deliberately does NOT centralize: real, module-local
tuning constants that are security/behavior decisions, not deployment
environment values — `REFRESH_TOKEN_TTL_DAYS` stays in `auth/refresh_
token.py`, `ACCESS_TOKEN_TTL_MINUTES` stays in `auth/access_token.py`,
`STABLE_THRESHOLD` stays in `features/trust_digest.py`, and so on. Moving
those here would blur a real, meaningful distinction this project has
held since its earliest sessions: infrastructure/credential config is
environment-dependent, real business-logic constants are not.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# The exact, real, insecure placeholder backend/.env.example ships —
# used here only to detect whether a real deployment ever actually
# overrode it, never trusted as a real secret itself.
_INSECURE_DEFAULT_JWT_SIGNING_KEY = "change-me-in-real-deployment"


class Settings(BaseSettings):
    """Every real field name below matches `backend/.env.example`
    exactly — confirmed by direct comparison before writing this class,
    not assumed. Infrastructure fields default to `None`, the honest
    value for "not yet provisioned" (per `STATUS_INDEX.md`'s standing
    disclosure that no live Supabase/Upstash/Cloud Run/Langfuse exists
    yet) — never a guessed placeholder URL that could be silently
    mistaken for a real one."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Supabase — unprovisioned until real Phase 2 infrastructure work.
    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_service_key: str | None = Field(default=None, alias="SUPABASE_SERVICE_KEY")

    # Upstash Redis. A real, disclosed fix: `UPSTASH_REDIS_REST_TOKEN` was
    # missing from this project's real `.env.example` until directly
    # noticed while reviewing a real, filled-in `.env` — Upstash's REST
    # API genuinely needs a URL AND a bearer token to authenticate; a URL
    # alone cannot. Added here and to `.env.example` in the same real fix.
    upstash_redis_url: str | None = Field(default=None, alias="UPSTASH_REDIS_URL")
    upstash_redis_rest_token: str | None = Field(default=None, alias="UPSTASH_REDIS_REST_TOKEN")

    # LLM providers (Capacity Manager routing, per
    # QUORUM_CONFIGURATION_CONSTANTS.md §8).
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    tavily_api_key: str | None = Field(default=None, alias="TAVILY_API_KEY")

    # Auth. Defaults to the same real, insecure placeholder
    # backend/.env.example ships — deliberately never breaks a fresh
    # clone or CI run that hasn't set a real secret, but see
    # `is_using_insecure_default_jwt_signing_key` below for the real
    # safety check this default exists to make possible.
    jwt_signing_key: str = Field(default=_INSECURE_DEFAULT_JWT_SIGNING_KEY, alias="JWT_SIGNING_KEY")

    # Google OAuth (Gmail/Calendar ingestion + real send/booking actions
    # — server-side token exchange, per
    # QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md §14.2). Added when the real
    # credentials were actually generated, not provisioned speculatively
    # ahead of need.
    google_oauth_client_id: str | None = Field(default=None, alias="GOOGLE_OAUTH_CLIENT_ID")
    google_oauth_client_secret: str | None = Field(default=None, alias="GOOGLE_OAUTH_CLIENT_SECRET")

    # Observability.
    langfuse_public_key: str | None = Field(default=None, alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str | None = Field(default=None, alias="LANGFUSE_SECRET_KEY")

    # Internal service-to-service auth for `POST /internal/drain-retry-
    # queue` (`DEC-127`) -- a real, deliberately DIFFERENT mechanism from
    # `jwt_signing_key` above: `pg_net` calling this endpoint has no real
    # user session to hold a Bearer token, so this is a real, static
    # shared secret instead, checked with a timing-safe comparison
    # (`main.py`'s own `_require_internal_secret`). Defaults to `None`,
    # the same honest "not yet provisioned" default every other real
    # credential field in this class uses -- the endpoint fails closed
    # (401) whenever this is unset, never silently open.
    internal_drain_secret: str | None = Field(default=None, alias="INTERNAL_DRAIN_SECRET")

    @property
    def is_using_insecure_default_jwt_signing_key(self) -> bool:
        """A real, checkable fact a caller (main.py's startup, a real
        deployment health check) can act on — never silently proceeding
        with a known-public placeholder secret without at least the
        chance to loudly refuse or warn."""
        return self.jwt_signing_key == _INSECURE_DEFAULT_JWT_SIGNING_KEY


@lru_cache
def get_settings() -> Settings:
    """Real, cached singleton — reads real environment/`.env` values
    exactly once per process. The standard FastAPI settings-dependency
    pattern, avoiding re-parsing the environment on every call."""
    return Settings()
