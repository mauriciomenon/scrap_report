"""Utilities to prevent sensitive data leakage in logs and payloads."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from .sensitive_patterns import (
    BEARER_TOKEN_VALUE_CHARCLASS,
    SENSITIVE_KEYWORDS,
    SENSITIVE_REDACTION_KEYWORD_PATTERN,
)

BEARER_TOKEN_PATTERN = re.compile(rf"(?i)\bBearer\s+{BEARER_TOKEN_VALUE_CHARCLASS}+")
SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    rf"\b(?P<assign_key>{SENSITIVE_REDACTION_KEYWORD_PATTERN})\b(?P<assign_sep>\s*[:=]\s*)"
    rf"(?P<assign_value>\"[^\"]*\"|'[^']*'|[^,;\r\n]+?)"
    rf"(?=(?:\s+\b{SENSITIVE_REDACTION_KEYWORD_PATTERN}\b\s*[:=])|[,;]|\s*$)",
    re.IGNORECASE,
)
SENSITIVE_STANDALONE_PATTERN = re.compile(
    rf"(?<![A-Za-z0-9_])(?P<standalone_key>{SENSITIVE_REDACTION_KEYWORD_PATTERN})"
    rf"(?![A-Za-z0-9_]|\s*[:=])",
    re.IGNORECASE,
)

ALLOWED_SAFE_KEYS = {
    "secret_set",
    "secret_found",
    "secret_result",
}
SENSITIVE_KEY_COMPONENT_PARTS = tuple(
    re.escape(keyword) for keyword in sorted(SENSITIVE_KEYWORDS)
)
SENSITIVE_KEY_COMPONENT_PATTERN = re.compile(
    rf"(^|[^a-z0-9])(?:{'|'.join(SENSITIVE_KEY_COMPONENT_PARTS)})([^a-z0-9]|$)"
)
SAFE_KEY_COMPONENT_PATTERN = re.compile(
    rf"(^|[^a-z0-9])(?P<safe>{'|'.join(re.escape(key) for key in sorted(ALLOWED_SAFE_KEYS))})([^a-z0-9]|$)"
)


@lru_cache(maxsize=512)
def _is_effectively_safe_key(key_l: str) -> bool:
    if key_l in ALLOWED_SAFE_KEYS:
        return True
    if not SAFE_KEY_COMPONENT_PATTERN.search(key_l):
        return False
    scrubbed = SAFE_KEY_COMPONENT_PATTERN.sub(" ", key_l)
    return not bool(SENSITIVE_KEY_COMPONENT_PATTERN.search(scrubbed))


def redact_text(value: str) -> str:
    def _replace_assignment(match: re.Match[str]) -> str:
        return f"{match.group('assign_key')}{match.group('assign_sep')}***"

    def _replace_standalone(match: re.Match[str]) -> str:
        standalone = match.group("standalone_key")
        return f"{standalone} ***"

    text = BEARER_TOKEN_PATTERN.sub("Bearer ***", value)
    text = SENSITIVE_ASSIGNMENT_PATTERN.sub(_replace_assignment, text)
    text = SENSITIVE_STANDALONE_PATTERN.sub(_replace_standalone, text)
    return text


def assert_no_sensitive_fields(payload: dict[str, Any]) -> None:
    max_depth = 128

    stack: list[tuple[Any, str, int]] = [(payload, "root", 0)]
    visited_nodes: set[int] = set()
    while stack:
        node, trail, depth = stack.pop()
        if depth > max_depth:
            raise ValueError(f"payload excede profundidade maxima segura: {trail}")
        if isinstance(node, dict):
            node_id = id(node)
            if node_id in visited_nodes:
                continue
            visited_nodes.add(node_id)
            for key, val in node.items():
                key_l = str(key).lower()
                is_safe_key = _is_effectively_safe_key(key_l)
                has_sensitive_marker = bool(SENSITIVE_KEY_COMPONENT_PATTERN.search(key_l))
                if has_sensitive_marker and not is_safe_key:
                    raise ValueError(f"payload contem campo sensivel proibido: {trail}.{key}")
                next_depth = depth + 1 if isinstance(val, (dict, list)) else depth
                stack.append((val, f"{trail}.{key}", next_depth))
        elif isinstance(node, list):
            node_id = id(node)
            if node_id in visited_nodes:
                continue
            visited_nodes.add(node_id)
            for idx, item in enumerate(node):
                next_depth = depth + 1 if isinstance(item, (dict, list)) else depth
                stack.append((item, f"{trail}[{idx}]", next_depth))
