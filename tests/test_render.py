import shutil
import pytest
from ai_event_editor.render import render

def test_rejects_missing_timeline(tmp_path):
    with pytest.raises(ValueError):
        render({"fps": 25, "segments": []}, tmp_path / "out.mp4")

def test_refuses_to_drop_speed_effects(tmp_path):
    plan = {"fps": 25, "segments": [{"speed_effect": {"kind": "ramp"}}]}
    with pytest.raises(ValueError, match="Speed effects require"):
        render(plan, tmp_path / "out.mp4")

@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg unavailable")
def test_short_synthetic_mp4(tmp_path):
    import subprocess
    source = tmp_path / "input.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "color=c=blue:s=320x180:r=25:d=2",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source)], check=True)
    plan = {"fps": 25, "duration_frames": 25,
            "segments": [{"path": str(source), "duration_frames": 25,
                          "source_in_seconds": 0, "speed_effect": {"kind": "normal"}}]}
    output = tmp_path / "output.mp4"
    assert render(plan, output, width=320, height=180) == str(output)
    assert output.stat().st_size > 1000
