"""Real tests for core/config.py."""
import pytest

from quorum_backend.core.config import Settings, get_settings


def _clear_real_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """A real, deliberate isolation step -- this machine's own shell may
    genuinely have some of these set (e.g. during real infra work later
    in this project), and these tests must prove Settings' own defaults,
    not whatever happens to be in this process's real environment.

    RESOLVED, a real, live CI failure (`DEC-181`'s own merge-triggered
    `main` run): this list was genuinely incomplete -- missing
    `GOOGLE_TOKEN_ENCRYPTION_KEY`, `INTERNAL_DRAIN_SECRET`,
    `FIREBASE_PROJECT_ID`, `FIREBASE_SERVICE_ACCOUNT_JSON` -- and this
    developer's own local shell simply doesn't happen to have those set
    globally, so every real `__repr__` redaction test passed locally by
    accident. CI's own real job environment DOES set a real
    `GOOGLE_TOKEN_ENCRYPTION_KEY` for the whole job (confirmed directly
    from that run's own env dump), producing a real, live, environment-
    dependent test failure the moment `test_repr_redacts_every_real_
    secret_shaped_field` ran there -- the exact same class of bug
    already found and fixed once tonight for a different test
    (`test_quick_capture_logs_a_real_fallback_line...`, `DEC-175`'s own
    hotfix). Every one of `Settings`' real 16 credential-shaped fields
    is now cleared here, matching `QUORUM_PRODUCTION_READINESS_AUDIT_
    PLAN.md` §8's own real, current inventory exactly -- not just the
    ones convenient to this one local machine's own ambient shell."""
    for name in [
        "SUPABASE_URL", "SUPABASE_SERVICE_KEY", "UPSTASH_REDIS_URL",
        "UPSTASH_REDIS_REST_TOKEN", "GEMINI_API_KEY", "GROQ_API_KEY",
        "TAVILY_API_KEY", "JWT_SIGNING_KEY", "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY", "GOOGLE_OAUTH_CLIENT_ID",
        "GOOGLE_OAUTH_CLIENT_SECRET", "GOOGLE_TOKEN_ENCRYPTION_KEY",
        "INTERNAL_DRAIN_SECRET", "FIREBASE_PROJECT_ID",
        "FIREBASE_SERVICE_ACCOUNT_JSON",
    ]:
        monkeypatch.delenv(name, raising=False)


def test_infrastructure_fields_default_to_none_not_a_guessed_placeholder(monkeypatch):
    _clear_real_env_vars(monkeypatch)
    settings = Settings(_env_file=None)

    assert settings.supabase_url is None
    assert settings.supabase_service_key is None
    assert settings.upstash_redis_url is None
    assert settings.upstash_redis_rest_token is None
    assert settings.gemini_api_key is None
    assert settings.groq_api_key is None
    assert settings.tavily_api_key is None
    assert settings.langfuse_public_key is None
    assert settings.langfuse_secret_key is None
    assert settings.google_oauth_client_id is None
    assert settings.google_oauth_client_secret is None


def test_jwt_signing_key_defaults_to_the_real_env_example_placeholder(monkeypatch):
    _clear_real_env_vars(monkeypatch)
    settings = Settings(_env_file=None)
    assert settings.jwt_signing_key == "change-me-in-real-deployment"


def test_is_using_insecure_default_is_true_on_the_real_unmodified_default(monkeypatch):
    _clear_real_env_vars(monkeypatch)
    settings = Settings(_env_file=None)
    assert settings.is_using_insecure_default_jwt_signing_key is True


def test_is_using_insecure_default_is_false_once_a_real_secret_is_set(monkeypatch):
    _clear_real_env_vars(monkeypatch)
    monkeypatch.setenv("JWT_SIGNING_KEY", "a-real-generated-production-secret")
    settings = Settings(_env_file=None)
    assert settings.is_using_insecure_default_jwt_signing_key is False


def test_real_env_vars_are_read_via_their_exact_env_example_names(monkeypatch):
    _clear_real_env_vars(monkeypatch)
    monkeypatch.setenv("SUPABASE_URL", "postgresql://real-real-real")
    monkeypatch.setenv("GEMINI_API_KEY", "real-gemini-key")

    settings = Settings(_env_file=None)

    assert settings.supabase_url == "postgresql://real-real-real"
    assert settings.gemini_api_key == "real-gemini-key"


def test_upstash_rest_token_is_read_via_its_own_real_env_var_name(monkeypatch):
    # A real, disclosed fix: UPSTASH_REDIS_REST_TOKEN was missing from
    # this project's real .env.example until directly noticed reviewing
    # a real, filled-in .env -- Upstash's REST API needs a URL AND a
    # bearer token; a URL alone cannot authenticate.
    _clear_real_env_vars(monkeypatch)
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "a-real-upstash-rest-token")
    settings = Settings(_env_file=None)
    assert settings.upstash_redis_rest_token == "a-real-upstash-rest-token"


def test_google_oauth_fields_are_read_via_their_own_real_env_var_names(monkeypatch):
    _clear_real_env_vars(monkeypatch)
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "real-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "real-client-secret")

    settings = Settings(_env_file=None)

    assert settings.google_oauth_client_id == "real-client-id.apps.googleusercontent.com"
    assert settings.google_oauth_client_secret == "real-client-secret"


def test_an_unrelated_real_environment_variable_never_causes_a_validation_error(monkeypatch):
    # A real, defensive property: this process's real environment has
    # many variables Settings knows nothing about (PATH, JAVA_HOME,
    # ANDROID_HOME, etc.) -- none of them should ever break settings
    # loading.
    monkeypatch.setenv("SOME_COMPLETELY_UNRELATED_VARIABLE", "x")
    Settings(_env_file=None)  # must not raise


def test_get_settings_returns_a_real_cached_singleton():
    first = get_settings()
    second = get_settings()
    assert first is second


# --- __repr__ secret redaction (QUORUM_PRODUCTION_READINESS_AUDIT_PLAN.md
# §8's own disclosed, real, pre-existing latent risk, closed here) ---


def test_repr_redacts_every_real_secret_shaped_field(monkeypatch):
    _clear_real_env_vars(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "a-real-gemini-key-that-must-never-appear-in-a-repr")
    monkeypatch.setenv("JWT_SIGNING_KEY", "a-real-signing-key-that-must-never-appear-in-a-repr")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "a-real-oauth-secret-that-must-never-appear-in-a-repr")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "a-real-token-that-must-never-appear-in-a-repr")
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_JSON", '{"private_key": "a-real-rsa-key-that-must-never-appear-in-a-repr"}')

    settings = Settings(_env_file=None)
    rendered = repr(settings)

    assert "a-real-gemini-key-that-must-never-appear-in-a-repr" not in rendered
    assert "a-real-signing-key-that-must-never-appear-in-a-repr" not in rendered
    assert "a-real-oauth-secret-that-must-never-appear-in-a-repr" not in rendered
    assert "a-real-token-that-must-never-appear-in-a-repr" not in rendered
    assert "a-real-rsa-key-that-must-never-appear-in-a-repr" not in rendered
    assert rendered.count("***REDACTED***") == 5


def test_str_matches_repr_redaction_too(monkeypatch):
    _clear_real_env_vars(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "a-real-gemini-key-that-must-never-appear-in-a-repr")
    settings = Settings(_env_file=None)
    assert "a-real-gemini-key-that-must-never-appear-in-a-repr" not in str(settings)


def test_repr_leaves_genuinely_non_secret_identifiers_visible(monkeypatch):
    # A real, deliberate choice: redacting every field would make this
    # repr useless for real debugging without closing any real exposure
    # -- a project ref or a client ID is not itself a secret.
    _clear_real_env_vars(monkeypatch)
    monkeypatch.setenv("SUPABASE_URL", "postgresql://a-real-visible-project-ref")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "a-real-visible-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "a-real-visible-firebase-project-id")

    rendered = repr(Settings(_env_file=None))

    assert "a-real-visible-project-ref" in rendered
    assert "a-real-visible-client-id.apps.googleusercontent.com" in rendered
    assert "a-real-visible-firebase-project-id" in rendered


def test_repr_redacts_a_real_default_insecure_jwt_signing_key_too(monkeypatch):
    # Even the real, disclosed, public default placeholder is redacted
    # -- this repr's own redaction is name-based, not value-based, and
    # should never need to distinguish "a real secret" from "a known
    # public placeholder that happens to live in the same field."
    _clear_real_env_vars(monkeypatch)
    settings = Settings(_env_file=None)
    assert "change-me-in-real-deployment" not in repr(settings)
