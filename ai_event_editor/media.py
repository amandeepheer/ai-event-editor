"""Inspect local media with ffprobe."""
import json
import subprocess
from pathlib import Path
SUPPORTED = {".mp4", ".mov", ".mxf", ".m4v"}
def scan(folder: str) -> list[dict]:
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")
    results = []
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in SUPPORTED:
            continue
        results.append(probe(path))
    return results


def probe(path):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    command = ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,avg_frame_rate:stream_disposition=attached_pic", "-of", "json", str(path)]
    proc = subprocess.run(command, capture_output=True, text=True, check=True)
    info = json.loads(proc.stdout)
    return {"path": str(path), "duration": float(info.get("format", {}).get("duration", 0)), "streams": info.get("streams", [])}
