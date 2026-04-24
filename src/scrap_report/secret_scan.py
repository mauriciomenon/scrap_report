"""Local secret scanner for pre-run safety checks."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .sensitive_patterns import (
    API_KEY_KEYWORD_PATTERN,
    BEARER_TOKEN_VALUE_CHARCLASS,
    PASSWORD_KEYWORD_PATTERN,
)

SUPPORTED_SCAN_SUFFIXES = {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".env"}
DEFAULT_PATTERNS: dict[str, re.Pattern[str]] = {
    "sam_password_env": re.compile(r"SAM_PASSWORD\s*=", re.IGNORECASE),
    "inline_password_key": re.compile(
        rf"{PASSWORD_KEYWORD_PATTERN}\s*[:=]\s*['\"](?=[^'\"]{{8,}})[^'\"]+['\"]",
        re.IGNORECASE,
    ),
    "bearer_token": re.compile(rf"Bearer\s+{BEARER_TOKEN_VALUE_CHARCLASS}{{20,}}", re.IGNORECASE),
    "api_key_inline": re.compile(
        rf"{API_KEY_KEYWORD_PATTERN}\s*[:=]\s*['\"](?=[^'\"]{{12,}})[^'\"]+['\"]",
        re.IGNORECASE,
    ),
}
COMBINED_SECRET_PATTERN = re.compile(
    "|".join(f"(?P<{name}>{pattern.pattern})" for name, pattern in DEFAULT_PATTERNS.items()),
    re.IGNORECASE,
)
MULTILINE_TRIGGER_PATTERN = re.compile(
    rf"(?:SAM_PASSWORD|{PASSWORD_KEYWORD_PATTERN}|{API_KEY_KEYWORD_PATTERN})\s*[:=]\s*$",
    re.IGNORECASE,
)
MAX_MULTILINE_FOLLOWUP_LINES = 3


@dataclass(slots=True)
class SecretFinding:
    path: str
    line: int
    rule: str
    excerpt: str


def _record_finding(
    *,
    findings: list[SecretFinding],
    seen_findings: set[tuple[str, int, str, str]],
    candidate: Path,
    line: int,
    rule: str,
    excerpt: str,
) -> None:
    finding_key = (str(candidate), line, rule, excerpt)
    if finding_key in seen_findings:
        return
    seen_findings.add(finding_key)
    findings.append(
        SecretFinding(
            path=str(candidate),
            line=line,
            rule=rule,
            excerpt=excerpt,
        )
    )


def _iter_match_rules(scan_text: str) -> Iterator[tuple[str, int]]:
    for match in COMBINED_SECRET_PATTERN.finditer(scan_text):
        rule = match.lastgroup
        if rule:
            yield rule, match.start()


def _iter_line_findings(lines: Iterator[str]) -> Iterator[tuple[int, str, str]]:
    seen_findings: set[tuple[int, str, str]] = set()
    pending_windows: list[tuple[int, str, str, int]] = []
    for line_number, line in enumerate(lines, start=1):
        current_excerpt = line.strip()[:200]
        for rule, _ in _iter_match_rules(line):
            finding_key = (line_number, rule, current_excerpt)
            if finding_key in seen_findings:
                continue
            seen_findings.add(finding_key)
            yield line_number, rule, current_excerpt

        next_pending_windows: list[tuple[int, str, str, int]] = []
        for anchor_line, anchor_excerpt, pending_text, remaining_lines in pending_windows:
            multiline_text = f"{pending_text}{line}"
            boundary = len(pending_text)
            for rule, match_start in _iter_match_rules(multiline_text):
                if match_start >= boundary:
                    continue
                finding_key = (anchor_line, rule, anchor_excerpt)
                if finding_key in seen_findings:
                    continue
                seen_findings.add(finding_key)
                yield anchor_line, rule, anchor_excerpt
            if remaining_lines > 1:
                next_pending_windows.append(
                    (anchor_line, anchor_excerpt, multiline_text, remaining_lines - 1)
                )
        pending_windows = next_pending_windows

        current_content = line.rstrip("\r\n")
        if MULTILINE_TRIGGER_PATTERN.search(current_content):
            pending_windows.append(
                (line_number, current_excerpt, line, MAX_MULTILINE_FOLLOWUP_LINES)
            )


def _normalize_scan_roots(paths: list[Path]) -> list[Path]:
    resolved_paths: list[Path] = []
    seen_roots: set[Path] = set()
    for path in paths:
        if not path.exists():
            continue
        resolved = path.resolve()
        if resolved in seen_roots:
            continue
        seen_roots.add(resolved)
        resolved_paths.append(resolved)

    normalized_paths: list[Path] = []
    normalized_dirs: set[Path] = set()
    for resolved in sorted(resolved_paths, key=lambda item: (len(item.parts), str(item))):
        if resolved.is_dir():
            if any(parent in normalized_dirs for parent in resolved.parents):
                continue
            normalized_dirs.add(resolved)
        normalized_paths.append(resolved)
    return normalized_paths


def _iter_scan_candidates(path: Path) -> Iterator[Path]:
    if path.is_file():
        if path.suffix.lower() in SUPPORTED_SCAN_SUFFIXES:
            yield path
        return

    for root, dirs, files in os.walk(path):
        dirs.sort()
        files.sort()
        root_path = Path(root)
        for file_name in files:
            item = root_path / file_name
            if item.suffix.lower() in SUPPORTED_SCAN_SUFFIXES:
                yield item


def _scan_file(candidate: Path) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    seen_findings: set[tuple[str, int, str, str]] = set()
    with candidate.open("r", encoding="utf-8", errors="ignore") as handle:
        for line_number, rule, excerpt in _iter_line_findings(handle):
            _record_finding(
                findings=findings,
                seen_findings=seen_findings,
                candidate=candidate,
                line=line_number,
                rule=rule,
                excerpt=excerpt,
            )
    return findings


def scan_paths(paths: list[Path]) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    normalized_paths = _normalize_scan_roots(paths)
    scanned_files: set[Path] = set()
    for path in normalized_paths:
        for candidate in _iter_scan_candidates(path):
            resolved_candidate = candidate.resolve()
            if resolved_candidate in scanned_files:
                continue
            scanned_files.add(resolved_candidate)
            findings.extend(_scan_file(resolved_candidate))
    return findings

