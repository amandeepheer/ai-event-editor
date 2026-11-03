import xml.etree.ElementTree as ET
import pytest
from ai_event_editor.music import AudioRange, preview_audio
from ai_event_editor.xml_export import export

def test_precise_range():
    selected = AudioRange(30.2, 200.5).validate()
    assert selected.duration == pytest.approx(170.3)

@pytest.mark.parametrize("start,end", [(-1,10),(5,5),(10,5),(float("nan"),10),(0,float("inf"))])
def test_invalid_range(start,end):
    with pytest.raises(ValueError):
        AudioRange(start,end).validate()

def test_xml_uses_original_audio_offset(tmp_path):
    plan = {"fps":25,"duration_frames":1500,"segments":[]}
    out = tmp_path / "edit.xml"
    export(plan,str(out),"/original/song.mp3",audio_start=30.2,audio_end=200.5)
    root = ET.parse(out).getroot()
    clip = root.find(".//audio/track/clipitem")
    assert clip.findtext("in") == "755"
    assert clip.findtext("out") == "2255"
    assert clip.findtext("start") == "0"
    assert clip.findtext("end") == "1500"
    assert "song.mp3" in clip.findtext("file/pathurl")

def test_reject_short_excerpt(tmp_path):
    with pytest.raises(ValueError, match="shorter"):
        export({"fps":25,"duration_frames":1500,"segments":[]},str(tmp_path/"x.xml"),"song.mp3",30.2,60.2)

def test_preview_command_no_mutation(tmp_path,monkeypatch):
    original = tmp_path/"song.mp3"
    original.write_bytes(b"unchanged")
    calls=[]
    monkeypatch.setattr("ai_event_editor.music.subprocess.run", lambda args,check: calls.append((args,check)))
    preview_audio(str(original),30.2,200.5)
    assert calls[0][0][0] == "ffplay"
    assert calls[0][0][-1] == str(original)
    assert original.read_bytes() == b"unchanged"
