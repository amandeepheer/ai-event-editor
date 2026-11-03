import pytest
from ai_event_editor.planner import Shot, ORDER, plan

def shots():
    return [Shot(f"/sample/{cat}-{i}.mp4", cat, 0, 5) for cat in ORDER for i in range(45)]

@pytest.mark.parametrize("duration", [30, 45, 60, 90, 120, 180, 300])
def test_duration_exact(duration):
    result = plan(shots(), [], duration=duration)
    assert result["duration_frames"] == duration * 25
    assert result["duration_seconds"] == duration
    assert sum(s["duration_frames"] for s in result["segments"]) == duration * 25
    assert result["segments"][-1]["timeline_start"] + result["segments"][-1]["duration_frames"] == duration * 25

@pytest.mark.parametrize("duration", [0, 29, 301, 60.5, True])
def test_invalid_duration(duration):
    with pytest.raises(ValueError):
        plan(shots(), [], duration=duration)

def test_not_enough_footage_for_five_minutes():
    with pytest.raises(ValueError, match="Insufficient unique footage"):
        plan([Shot(f"/sample/{cat}.mp4", cat, 0, 5) for cat in ORDER], [], duration=300)
