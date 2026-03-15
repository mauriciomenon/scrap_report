"""Selector resilience engine with prioritized fallback strategies."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass


@dataclass(slots=True)
class SelectorCandidate:
    selector: str
    score: int
    source: str


def build_candidates(
    stable_id: str | None = None,
    name: str | None = None,
    aria_label: str | None = None,
    text: str | None = None,
    xpath: str | None = None,
) -> list[SelectorCandidate]:
    candidates: list[SelectorCandidate] = []
    if stable_id:
        candidates.append(SelectorCandidate(stable_id, 100, "id"))
    if name:
        candidates.append(SelectorCandidate(name, 90, "name"))
    if aria_label:
        candidates.append(SelectorCandidate(aria_label, 80, "aria"))
    if text:
        candidates.append(SelectorCandidate(text, 70, "text"))
    if xpath:
        candidates.append(SelectorCandidate(xpath, 60, "xpath"))
    return sorted(candidates, key=lambda item: item.score, reverse=True)


def pick_best_available(
    candidates: Iterable[SelectorCandidate], is_available: Callable[[str], bool]
) -> SelectorCandidate | None:
    for candidate in candidates:
        if is_available(candidate.selector):
            return candidate
    return None


def filter_candidates_for_mode(
    candidates: list[SelectorCandidate], mode: str
) -> list[SelectorCandidate]:
    if mode == "strict":
        return [item for item in candidates if item.score >= 90]
    return candidates
