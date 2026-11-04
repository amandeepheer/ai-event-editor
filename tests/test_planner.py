import xml.etree.ElementTree as ET
import pytest
from ai_event_editor.planner import Shot, plan, FPS, ORDER
from ai_event_editor.xml_export import export
def fixture_shots():
    return [Shot(f"/example/{category}{n}.mp4", category, 0, 5, .9 - n * .01) for category in ORDER for n in range(6)]
def test_exact_60_and_order():
    result = plan(fixture_shots(), list(range(1, 60)))
    assert sum(s["duration_frames"] for s in result["segments"]) == 60 * FPS
    assert result["segments"][0]["category"] == "drone"
    assert result["segments"][-1]["category"] == "finale"
    assert {s["category"] for s in result["segments"]} == set(ORDER)
    assert all(a["timeline_start"] + a["duration_frames"] == b["timeline_start"] for a, b in zip(result["segments"], result["segments"][1:]))
def test_missing_category():
    result = plan(fixture_shots()[:-6], [])
    assert result["duration_frames"] == 1500
    assert "finale" in result["missing_categories"]
    assert all(s["category"] != "finale" for s in result["segments"])
def test_insufficient_footage():
    with pytest.raises(ValueError, match="Insufficient unique footage"):
        plan([Shot(f"/example/{cat}.mp4", cat, 0, 2) for cat in ORDER], [])
def test_export_well_formed(tmp_path):
    p = tmp_path / "recap.xml"
    result = plan(fixture_shots(), [])
    export(result, str(p), "/example/music.wav")
    tree = ET.parse(p)
    assert tree.getroot().tag == "xmeml"
    assert tree.findtext(".//sequence/duration") == "1500"
    assert len(tree.findall(".//video/track/clipitem")) == len(result["segments"])
    assert len(tree.findall(".//audio/track/clipitem")) == 1
def test_bad_shot():
    with pytest.raises(ValueError):
        Shot.from_dict({"path": "a.mp4", "category": "drone", "start": 4, "end": 2})

@pytest.mark.parametrize('beats', [[], list(range(30))])
def test_many_high_ranked_windows_do_not_monopolize_edit(beats):
    shots = [Shot(path, 'performance', i*4, (i+1)*4, quality=quality)
             for path, quality in [('pooja.mp4', .9), ('gatka.mp4', .7), ('crowd.mp4', .5)]
             for i in range(30)]
    result = plan(shots, beats, duration=30)
    paths = [s['path'] for s in result['segments']]
    assert paths[:3] == ['pooja.mp4', 'gatka.mp4', 'crowd.mp4']
    assert set(paths) == {s.path for s in shots}
    assert result == plan(list(reversed(shots)), beats, duration=30)

def test_long_sources_rotate_and_never_reuse_ranges():
    result = plan([Shot(p, 'performance', 0, 60) for p in ['a.mp4','b.mp4','c.mp4']], [], duration=60)
    paths = [s['path'] for s in result['segments']]
    assert all(a != b for a, b in zip(paths, paths[1:]))
    for path in set(paths):
        spans = [(s['source_in_seconds'], s['source_in_seconds']+s['duration_frames']/FPS)
                 for s in result['segments'] if s['path']==path]
        assert all(end <= start+1e-7 for (_,end),(start,_) in zip(spans,spans[1:]))

def test_pins_and_short_sources_survive_source_rotation():
    shots = [Shot('long.mp4','performance',0,60), Shot('short.mp4','performance',0,1),
             Shot('pin.mp4','performance',10,14,quality=0,id='pinned',must_include=True)]
    result = plan(shots, [], duration=30)
    assert result['segments'][0]['shot_id']=='pinned'
    assert {s['path'] for s in result['segments']} == {s.path for s in shots}
    assert result['duration_frames']==750

def test_limited_duration_reports_omitted_sources():
    shots = [Shot(str(i)+'.mp4', 'performance', 0, 10) for i in range(40)]
    result = plan(shots, [], duration=30)
    assert any('eligible source videos' in w for w in result['warnings'])
