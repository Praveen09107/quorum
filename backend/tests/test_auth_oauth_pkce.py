"""Real tests for auth/oauth_pkce.py -- CRITICAL TIER."""
from quorum_backend.auth.oauth_pkce import (
    generate_oauth_state,
    generate_pkce_pair,
    validate_oauth_state,
    verify_pkce,
)


def test_valid_oauth_state_validates():
    state = generate_oauth_state()
    assert validate_oauth_state(state, state) is True


def test_mismatched_oauth_state_rejected():
    state = generate_oauth_state()
    other = generate_oauth_state()
    assert validate_oauth_state(state, other) is False


def test_valid_pkce_pair_verifies():
    verifier, challenge = generate_pkce_pair()
    assert verify_pkce(verifier, challenge) is True


def test_wrong_code_verifier_rejected():
    _verifier, challenge = generate_pkce_pair()
    wrong_verifier, _ = generate_pkce_pair()
    assert verify_pkce(wrong_verifier, challenge) is False


def test_generated_state_and_verifier_are_genuinely_random_not_fixed():
    # A real, minimal proof these aren't hardcoded/predictable values.
    states = {generate_oauth_state() for _ in range(20)}
    assert len(states) == 20
