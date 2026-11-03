import math
import pytest
from ai_event_editor.planner import Shot, ORDER, plan
from ai_event_editor.dynamic_mix import DynamicMix
from ai_event_editor.speed_effects import speed_effect

def test_selected_candidate_extra_fields_are_accepted():
    shot = Shot.from_dict({"path": "clip.mp4", "category": "dancing",
                           "start": 1.5, "end": 6.0, "quality": 0.8,
                           "confidence": 0.9, "selection_score": 0.83,
                           "review_required": False})
    assert shot.start == 1.5

@pytest.mark.parametrize("fps", [float("nan"), float("inf"), -1, 0, True])
def test_invalid_source_fps_rejected(fps):
    with pytest.raises(ValueError):
        speed_effect("dancing", fps, 90)

@pytest.mark.parametrize("energy", [True, 50.5, -1, 101])
def test_invalid_energy_rejected(energy):
    with pytest.raises(ValueError):
        speed_effect("dancing", 50, energy)

def test_source_times_survive_planning():
    shots = [Shot(f"/sample/{cat}-{i}.mp4", cat, 2.5, 10.5, fps=50)
             for cat in ORDER for i in range(20)]
    result = plan(shots, [], mix=DynamicMix(energy=90), auto_speed=True)
    assert result["segments"][0]["source_in_seconds"] == 2.5
    assert result["segments"][0]["source_end_seconds"] == 10.5
    assert sum(s["duration_frames"] for s in result["segments"]) == 1500
