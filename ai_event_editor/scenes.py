"""Offline scene detection using FFmpeg's scene-change filter.

Output candidate intervals; these are not semantic AI labels.
"""
import re
import subprocess
from pathlib import Path

PTS = re.compile(r"pts_time:([0-9]+(?:\.[0-9]+)?)")

def detect_cuts(path: str, threshold: float = 0.35) -> list[float]:
    if not 0 < threshold < 1:
        raise ValueError("threshold must be between zero and one")
    if not Path(path).is_file():
        raise FileNotFoundError(path)
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-i", path,
           "-vf", f"select=gt(scene\\,{threshold}),showinfo",
           "-an", "-f", "null", "-"]
    process = subprocess.run(cmd, capture_output=True, text=True)
    if process.returncode:
        raise RuntimeError(process.stderr[-1500:])
    return sorted({float(x) for x in PTS.findall(process.stderr)})

def intervals(cuts: list[float], duration: float, minimum: float = 0.5) -> list[tuple[float, float]]:
    if duration <= 0:
        raise ValueError("duration must be positive")
    points = [0.0] + sorted({c for c in cuts if 0 < c < duration}) + [duration]
    return [(a, b) for a, b in zip(points, points[1:]) if b-a >= minimum]
