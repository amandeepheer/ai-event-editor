import pytest
from ai_event_editor.scenes import intervals, detect_cuts
from ai_event_editor.shot_selection import rank_candidates, coverage_report

def test_scene_intervals():
    assert intervals([2, 4, 4, 15], 6) == [(0, 2), (2, 4), (4, 6)]

def test_scene_rejects_invalid_duration():
    with pytest.raises(ValueError):
        intervals([], 0)

def test_scene_rejects_threshold_before_ffmpeg():
    with pytest.raises(ValueError):
        detect_cuts("nonexistent.mp4", 2)

def test_ranking_quality_and_confidence():
    shots = [{"path": "b.mp4", "category": "drone", "start": 0, "end": 4, "quality": 0.8, "confidence": 0.9},
             {"path": "a.mp4", "category": "drone", "start": 0, "end": 3, "quality": 0.95, "confidence": 0.9},
             {"path": "c.mp4", "category": "crowd", "start": 0, "end": 2, "confidence": 0.1}]
    ranked = rank_candidates(shots)
    assert [x["path"] for x in ranked["drone"]] == ["a.mp4", "b.mp4"]
    assert "crowd" not in ranked

def test_coverage_flags_missing():
    result = coverage_report([{"path": "x.mp4", "category": "drone", "start": 0, "end": 5}])
    assert result["ready_for_planning"]
    assert "performance" in result["missing_categories"]
