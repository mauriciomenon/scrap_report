import pytest

from scrap_report.redaction import assert_no_sensitive_fields, redact_text


def test_redact_text_masks_keywords():
    text = "password token authorization api_key bearer"
    redacted = redact_text(text)
    assert "password ***" in redacted
    assert "token ***" in redacted
    assert "authorization ***" in redacted
    assert "api_key ***" in redacted
    assert "bearer ***" in redacted.lower()


def test_redact_text_masks_assigned_values_and_bearer():
    text = "password=abc123 token:'xyz' Authorization: Bearer super.token.value"
    redacted = redact_text(text)
    assert "abc123" not in redacted
    assert "xyz" not in redacted
    assert "super.token.value" not in redacted
    assert "password=***" in redacted
    assert "token:***" in redacted
    assert "Authorization: ***" in redacted


def test_redact_text_masks_unquoted_multiword_secret():
    text = "secret = very long phrase with spaces"
    redacted = redact_text(text)
    assert "very long phrase with spaces" not in redacted
    assert "secret = ***" in redacted


def test_redact_text_masks_assignment_at_end_of_line():
    text = "api_key=abcdef1234567890"
    redacted = redact_text(text)
    assert "abcdef1234567890" not in redacted
    assert "api_key=***" in redacted


def test_assert_no_sensitive_fields_rejects_payload():
    with pytest.raises(ValueError):
        assert_no_sensitive_fields({"status": "ok", "password": "x"})


def test_assert_no_sensitive_fields_allows_safe_payload():
    assert_no_sensitive_fields({"status": "ok", "meta": {"count": 1}})


def test_assert_no_sensitive_fields_allows_safe_key_component_without_sensitive_prefix():
    assert_no_sensitive_fields({"status": "ok", "meta": {"my_secret_set": True}})


def test_assert_no_sensitive_fields_rejects_sensitive_prefix_plus_safe_component():
    with pytest.raises(ValueError):
        assert_no_sensitive_fields({"status": "ok", "meta": {"password_secret_found": True}})

