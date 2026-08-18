"""Real tests for security/trace_scrubbing.py."""
from quorum_backend.security.trace_scrubbing import SENSITIVE_PATTERNS, scrub_trace_content


def test_credit_card_number_is_redacted():
    result = scrub_trace_content("my card is 4111111111111111")
    assert "REDACTED" in result
    assert "4111111111111111" not in result


def test_aadhaar_style_id_is_redacted():
    result = scrub_trace_content("my id is 1234 5678 9012")
    assert "REDACTED" in result
    assert "1234 5678 9012" not in result


def test_otp_code_is_redacted_including_the_full_labeled_phrase():
    # A real, confirmed-not-assumed behavior: the otp_code pattern
    # captures a group, but since the replacement never references it,
    # re.sub replaces the ENTIRE matched phrase -- "OTP: 482913," not
    # just the bare digits.
    result = scrub_trace_content("your code is OTP: 482913, don't share it")
    assert "OTP: 482913" not in result
    assert "482913" not in result
    assert "REDACTED" in result


def test_non_sensitive_text_passes_through_unchanged():
    text = "the meeting is scheduled for Tuesday at 3pm"
    assert scrub_trace_content(text) == text


def test_multiple_sensitive_items_in_one_string_are_all_redacted():
    text = "card 4111111111111111 and id 1234 5678 9012 and OTP: 998877"
    result = scrub_trace_content(text)
    assert "4111111111111111" not in result
    assert "1234 5678 9012" not in result
    assert "998877" not in result
    assert result.count("REDACTED") == 3


def test_sensitive_patterns_has_exactly_the_three_real_categories():
    assert set(SENSITIVE_PATTERNS.keys()) == {"credit_card", "aadhaar_style_id", "otp_code"}
