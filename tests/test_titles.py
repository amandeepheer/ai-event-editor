import shutil
import pytest
from ai_event_editor.titles import validate_titles, filter_chain
from ai_event_editor.render import render

def test_editable_title_properties():
    result = validate_titles([{"text": "Diwali 2026", "start": 0, "end": 2,
                               "position": "center", "animation": "fade",
                               "color": "gold", "size": 56}], 3)
    assert result[0]["color"] == "gold"

@pytest.mark.parametrize("title", [
    {"text": "", "start": 0, "end": 1},
    {"text": "hello", "start": 2, "end": 1},
    {"text": "hello", "start": 0, "end": 4},
    {"text": "hello", "start": 0, "end": 1, "position": "side"},
    {"text": "hello", "start": 0, "end": 1, "color": "red;bad"},
])
def test_rejects_invalid_title(title):
    with pytest.raises(ValueError):
        validate_titles([title], 3)

def test_filter_uses_textfile(tmp_path):
    filters = filter_chain([{"text": "Pukekohe: Diwali's Night", "start": 0, "end": 2}], tmp_path, 3)
    assert "textfile=" in filters
    assert "Pukekohe" not in filters

@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg unavailable")
def test_render_with_title(tmp_path):
    import subprocess
    source = tmp_path / "source.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                    "-i", "color=c=blue:s=320x180:r=25:d=2", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", str(source)], check=True)
    plan = {"fps": 25, "duration_frames": 25,
            "segments": [{"path": str(source), "duration_frames": 25,
                          "source_in_seconds": 0, "speed_effect": {"kind": "normal"}}]}
    out = tmp_path / "title.mp4"
    render(plan, out, width=320, height=180,
           titles=[{"text": "DIWALI", "start": 0, "end": 1, "position": "center"}])
    assert out.stat().st_size > 1000
