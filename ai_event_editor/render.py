"""CPU-only FFmpeg renderer for timeline plans.

Speed effects are not applied here yet. Refuse to silently render them incorrectly.
"""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

def render(plan, output, music=None, audio_start=0, width=1280, height=720, ffmpeg="ffmpeg", titles=None):
    if shutil.which(ffmpeg) is None:
        raise RuntimeError("FFmpeg is required")
    if not plan.get("segments") or plan.get("fps", 0) <= 0:
        raise ValueError("Invalid timeline")
    fps = plan["fps"]
    segments = plan["segments"]
    if any(s.get("speed_effect", {}).get("kind", "normal") != "normal" for s in segments):
        raise ValueError("Speed effects require the Stage 3 retiming renderer; refusing to discard them")
    output = Path(output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="event-editor-") as temp:
        pieces = []
        for index, shot in enumerate(segments):
            path = Path(shot["path"]).expanduser().resolve()
            if not path.is_file():
                raise FileNotFoundError(path)
            part = Path(temp) / f"part-{index:05d}.mp4"
            duration = shot["duration_frames"] / fps
            start = shot["source_in_seconds"] if "source_in_seconds" in shot else shot["source_in_frame"] / fps
            command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                       "-ss", str(start), "-i", str(path), "-t", str(duration),
                       "-vf", f"fps={fps},scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1",
                       "-an", "-c:v", "libx264", "-preset", "veryfast",
                       "-pix_fmt", "yuv420p", "-r", str(fps), str(part)]
            subprocess.run(command, check=True)
            pieces.append(part)
        listing = Path(temp) / "concat.txt"
        listing.write_text("".join("file '" + str(p).replace("'", "'\\''") + "'\n" for p in pieces), encoding="utf-8")
        command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                   "-f", "concat", "-safe", "0", "-i", str(listing)]
        if music:
            if not Path(music).is_file():
                raise FileNotFoundError(music)
            command += ["-ss", str(audio_start), "-i", str(music)]
        from .titles import filter_chain
        title_filters = filter_chain(titles or [], temp, plan["duration_frames"] / fps)
        if title_filters:
            command += ["-vf", title_filters]
        command += ["-t", str(plan["duration_frames"] / fps),
                    "-map", "0:v:0"]
        if music:
            command += ["-map", "1:a:0", "-c:a", "aac", "-b:a", "192k"]
        command += ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(output)]
        subprocess.run(command, check=True)
    return str(output)

def render_file(plan_path, output, music=None, audio_start=0, titles_path=None):
    titles = json.loads(Path(titles_path).read_text(encoding="utf-8")) if titles_path else None
    return render(json.loads(Path(plan_path).read_text(encoding="utf-8")), output, music, audio_start, titles=titles)
