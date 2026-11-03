import pytest
from ai_event_editor.auto_selection import select_shots, selection_report

def candidate(path, category, start, end, confidence=0.8, quality=0.7):
    return dict(path=path, category=category, start=start, end=end,
                confidence=confidence, quality=quality)

def test_selects_highest_scored_nonoverlapping_source_globally():
    data = [candidate("a.mp4", "crowd", 0, 3, quality=0.4),
            candidate("a.mp4", "dancing", 1, 4, quality=0.9),
            candidate("a.mp4", "crowd", 4, 7, quality=0.6)]
    result = select_shots(data)
    assert len(result) == 2
    assert {(s["category"], s["start"]) for s in result} == {("dancing", 1), ("crowd", 4)}

def test_deterministic_independent_of_input_order():
    data = [candidate(f"{i}.mp4", "crowd", 0, 3, quality=i / 10) for i in range(8)]
    assert select_shots(data) == select_shots(list(reversed(data)))

def test_filters_invalid_and_too_short():
    data = [candidate("ok.mp4", "crowd", 0, 2),
            candidate("bad.mp4", "crowd", 2, 2.2),
            candidate("bad.mp4", "crowd", -1, 2),
            candidate("bad.mp4", "crowd", 0, 2, confidence=float("nan")),
            candidate("bad.mp4", "other", 0, 2)]
    assert len(select_shots(data)) == 1

def test_report_missing_categories():
    report = selection_report(select_shots([candidate("a", "crowd", 0, 2)]))
    assert report["selected"] == 1
    assert report["ready_for_current_planner"] is True
    assert "drone" in report["missing_categories"]

def test_per_category_limit():
    data = [candidate(str(i), "crowd", 0, 2) for i in range(5)]
    assert len(select_shots(data, max_per_category=2)) == 2

@pytest.mark.parametrize("threshold", [-1, 2, float("nan")])
def test_bad_threshold(threshold):
    with pytest.raises(ValueError):
        select_shots([], min_confidence=threshold)
