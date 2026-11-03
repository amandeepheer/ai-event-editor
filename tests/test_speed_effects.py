import pytest
from ai_event_editor.speed_effects import speed_effect
from ai_event_editor.planner import Shot, ORDER, plan
from ai_event_editor.dynamic_mix import DynamicMix

def test_normal_25fps():
    assert speed_effect("dancing", 25, 100)["kind"] == "normal"

def test_50fps_slow_motion():
    effect = speed_effect("performance", 50, 75)
    assert effect["kind"] == "slow_motion"
    assert effect["speed"] == 0.5

def test_100fps_ramp():
    effect = speed_effect("dancing", 100, 95)
    assert effect["kind"] == "ramp"
    assert effect["keyframes"][1]["speed"] == 0.25

def test_low_energy_disables_effect():
    assert speed_effect("dancing", 100, 20)["kind"] == "normal"

def test_non_action_scene_stays_normal():
    assert speed_effect("drone", 100, 100)["kind"] == "normal"

@pytest.mark.parametrize("fps,energy", [(0,75),(25,-1),(25,101)])
def test_invalid_parameters(fps, energy):
    with pytest.raises(ValueError):
        speed_effect("dancing", fps, energy)

def test_planner_opt_in_effects_and_duration():
    shots = [Shot(f"/test/{cat}-{i}.mp4", cat, 0, 8, fps=100) for cat in ORDER for i in range(20)]
    result = plan(shots, [], mix=DynamicMix(energy=95), auto_speed=True)
    assert sum(s["duration_frames"] for s in result["segments"]) == 1500
    assert any(s["speed_effect"]["kind"] == "ramp" for s in result["segments"])
    assert all(s["speed"] == 1.0 for s in result["segments"])
