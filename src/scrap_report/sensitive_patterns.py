"""Shared sensitive pattern constants for scanning and redaction."""

from __future__ import annotations

import re

SENSITIVE_KEYWORDS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "authorization",
    "bearer",
)

SENSITIVE_REDACTION_KEYWORD_PATTERN = "(?:" + "|".join(
    "api[_-]?key" if keyword == "api_key" else re.escape(keyword)
    for keyword in SENSITIVE_KEYWORDS
) + ")"
PASSWORD_KEYWORD_PATTERN = r"(?:password|passwd)"
API_KEY_KEYWORD_PATTERN = r"(?:api[_-]?key)"
BEARER_TOKEN_VALUE_CHARCLASS = r"[A-Za-z0-9._-]"
