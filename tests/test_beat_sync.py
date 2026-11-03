import pytest
from ai_event_editor.beat_sync import beat_frames, choose_cut
from ai_event_editor.dynamic_mix import DynamicMix
from ai_event_editor.planner import ORDER, Shot, plan

def footage():
    return [Shot(f"/sample/{cat}-{i}.mp4", cat, 0, 8) for cat in ORDER for i in range(30)]

def test_beat_frames_clean_and_deduplicated():
    assert beat_frames([0, 0.5, 0.5, float("nan"), -2, 61], 25, 1500) == [12]

def test_choose_cut_snaps_nearby_beat():
    assert choose_cut(100, 150, 100, 75, [173], 25, 75) == 73

def test_choose_cut_does_not_snap_far_away():
    assert choose_cut(100, 150, 100, 75, [130], 25, 75) == 75

def test_cut_respects_source_capacity():
    assert choose_cut(100, 100, 40, 75, [175], 25, 75) <= 40

def test_planner_aligns_internal_cuts_to_beats():
    beats = [i * 2.92 for i in range(1, 21)]
    result = plan(footage(), beats, mix=DynamicMix(energy=75))
    beat_positions = beat_frames(beats, 25, 1500)
    cuts = [s["timeline_start"] + s["duration_frames"] for s in result["segments"][:-1]]
    assert any(c in beat_positions for c in cuts)
    assert sum(s["duration_frames"] for s in result["segments"]) == 1500

def test_section_energy_changes_pacing():
    low = plan(footage(), [], mix=DynamicMix(energy=75), section_energy={"dancing": 10})
    high = plan(footage(), [], mix=DynamicMix(energy=75), section_energy={"dancing": 100})
    low_dance = [s for s in low["segments"] if s["category"] == "dancing"]
    high_dance = [s for s in high["segments"] if s["category"] == "dancing"]
    assert len(high_dance) >= len(low_dance)
    assert high["section_energy"]["dancing"] == 100

@pytest.mark.parametrize("overrides", [{"dancing":101},{"unknown":50},{"drone":True},{"drone":-1}])
def test_invalid_section_energy(overrides):
    with pytest.raises(ValueError):
        plan(footage(), [], mix=DynamicMix(), section_energy=overrides)
