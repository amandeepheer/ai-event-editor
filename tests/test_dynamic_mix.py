import pytest
from ai_event_editor.dynamic_mix import DynamicMix, assign_styles
from ai_event_editor.planner import Shot, ORDER, plan

def footage():
    return [Shot(f"/example/{category}{i}.mp4", category, 0, 8, .9) for category in ORDER for i in range(20)]

def test_auto_mix_75_assigns_multiple_styles():
    mix = DynamicMix()
    styles = assign_styles(mix, ORDER, [], 60)
    assert len(styles) == len(ORDER)
    assert len({s.slug for s in styles}) >= 3
    assert styles[0].slug == "cinematic"
    assert styles[3].slug == "social-reel"
    assert styles[4].slug == "wedding"

def test_exact_duration_and_section_styles():
    result = plan(footage(), [], duration=60, mix=DynamicMix())
    assert sum(s["duration_frames"] for s in result["segments"]) == 1500
    assert result["dynamic_mix"]["energy"] == 75
    assert len({s["edit_style"] for s in result["segments"]}) >= 3
    assert all(a["timeline_start"] + a["duration_frames"] == b["timeline_start"] for a, b in zip(result["segments"], result["segments"][1:]))

@pytest.mark.parametrize("energy", [-1, 101, True])
def test_bad_energy(energy):
    with pytest.raises(ValueError):
        DynamicMix(energy=energy).validate()

def test_invalid_style():
    with pytest.raises(ValueError):
        DynamicMix(selected=("unknown",)).validate()

def test_manual_not_claimed():
    with pytest.raises(ValueError):
        DynamicMix(mode="manual").validate()
