"""Local secret scanner for pre-run safety checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PATTERNS: dict[str, re.Pattern[str]] = {
    "sam_password_env": re.compile(r"SAM_PASSWORD\s*=", re.IGNORECASE),
    "inline_password_key": re.compile(r"(password|passwd)\s*[:=]\s*['\"].+['\"]", re.IGNORECASE),
    "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9._-]+", re.IGNORECASE),
    "api_key_inline": re.compile(r"api[_-]?key\s*[:=]\s*['\"].+['\"]", re.IGNORECASE),
}


@dataclass(slots=True)
class SecretFinding:
    path: str
    line: int
    rule: str
    excerpt: str


def scan_paths(paths: list[Path]) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        if path.suffix.lower() not in {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".env"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for idx, line in enumerate(text.splitlines(), start=1):
            for rule, pattern in DEFAULT_PATTERNS.items():
                if pattern.search(line):
                    findings.append(
                        SecretFinding(
                            path=str(path),
                            line=idx,
                            rule=rule,
                            excerpt=line.strip()[:200],
                        )
                    )
    return findings

