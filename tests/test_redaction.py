import pytest

from scrap_report.redaction import assert_no_sensitive_fields, redact_text


def test_redact_text_masks_keywords():
    text = "password token authorization api_key"
    redacted = redact_text(text)
    assert "password" not in redacted
    assert "token" not in redacted
    assert "authorization" not in redacted
    assert "api_key" not in redacted


def test_redact_text_masks_assigned_values_and_bearer():
    text = "password=abc123 token:'xyz' Authorization: Bearer super.token.value"
    redacted = redact_text(text)
    assert "abc123" not in redacted
    assert "xyz" not in redacted
    assert "super.token.value" not in redacted
    assert "*** ***" in redacted


def test_assert_no_sensitive_fields_rejects_payload():
    with pytest.raises(ValueError):
        assert_no_sensitive_fields({"status": "ok", "password": "x"})


def test_assert_no_sensitive_fields_allows_safe_payload():
    assert_no_sensitive_fields({"status": "ok", "meta": {"count": 1}})

