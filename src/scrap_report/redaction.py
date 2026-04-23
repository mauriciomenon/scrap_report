"""Utilities to prevent sensitive data leakage in logs and payloads."""

from __future__ import annotations

import re
from typing import Any

SENSITIVE_KEYWORDS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "authorization",
    "bearer",
)

SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(password|passwd|secret|token|api[_-]?key|authorization)\b(\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)
BEARER_TOKEN_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._-]+")

ALLOWED_SAFE_KEYS = {
    "secret_set",
    "secret_found",
    "secret_result",
}


def redact_text(value: str) -> str:
    text = BEARER_TOKEN_PATTERN.sub("Bearer ***", value)
    text = SENSITIVE_ASSIGNMENT_PATTERN.sub(lambda match: f"{match.group(1)}{match.group(2)}***", text)
    for keyword in SENSITIVE_KEYWORDS:
        text = text.replace(keyword, "***")
        text = text.replace(keyword.upper(), "***")
    return text


def assert_no_sensitive_fields(payload: dict[str, Any]) -> None:
    def _walk(node: Any, trail: str) -> None:
        if isinstance(node, dict):
            for key, val in node.items():
                key_l = str(key).lower()
                if key_l in ALLOWED_SAFE_KEYS:
                    _walk(val, f"{trail}.{key}")
                    continue
                if any(marker in key_l for marker in SENSITIVE_KEYWORDS):
                    raise ValueError(f"payload contem campo sensivel proibido: {trail}.{key}")
                _walk(val, f"{trail}.{key}")
        elif isinstance(node, list):
            for idx, item in enumerate(node):
                _walk(item, f"{trail}[{idx}]")

    _walk(payload, "root")
