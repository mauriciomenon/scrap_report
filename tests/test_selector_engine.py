from scrap_report.selector_engine import (
    build_candidates,
    filter_candidates_for_mode,
    pick_best_available,
)


def test_build_candidates_priority_order():
    candidates = build_candidates(
        stable_id="#id",
        name="[name='x']",
        aria_label="[aria-label='X']",
        text="text=X",
        xpath="//x",
    )
    assert [c.source for c in candidates] == ["id", "name", "aria", "text", "xpath"]


def test_pick_best_available_returns_first_match():
    candidates = build_candidates(stable_id="#id", name="[name='x']", text="text=X")
    found = pick_best_available(candidates, lambda s: s == "[name='x']")
    assert found is not None
    assert found.selector == "[name='x']"


def test_pick_best_available_none_when_no_match():
    candidates = build_candidates(stable_id="#id")
    assert pick_best_available(candidates, lambda _s: False) is None


def test_filter_candidates_for_mode_strict():
    candidates = build_candidates(stable_id="#id", text="text=X")
    filtered = filter_candidates_for_mode(candidates, "strict")
    assert [c.source for c in filtered] == ["id"]
