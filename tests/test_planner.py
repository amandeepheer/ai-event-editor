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
    with pytest.raises(ValueError, match="Missing required category"):
        plan(fixture_shots()[:-6], [])
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
