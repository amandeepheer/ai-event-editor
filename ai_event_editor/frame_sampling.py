"""Extract low-resolution stills from local video for vision analysis."""
from pathlib import Path
import subprocess

def extract_frame(video: str, timestamp: float, output: str, width: int = 512) -> str:
    if timestamp < 0 or width < 64 or width > 2048:
        raise ValueError("Invalid frame timestamp or width")
    if not Path(video).is_file():
        raise FileNotFoundError(video)
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
           "-ss", str(timestamp), "-i", video, "-frames:v", "1",
           "-vf", f"scale={width}:-2", str(destination)]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    if not destination.is_file():
        raise RuntimeError("FFmpeg did not generate the requested frame")
    return str(destination)
