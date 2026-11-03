"""Learn approximate cutting pace from finished reference videos.

FFmpeg scene detection can misidentify flashes and camera motion as cuts.
The result is a suggested style, not a clone of the original editor.
"""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
from statistics import median
from .media import scan
from .scenes import detect_cuts, intervals
from .styles import Style, PRESETS

def estimate_cut_lengths(duration: float, cuts: list[float]) -> list[float]:
    return [b-a for a, b in intervals(cuts, duration, minimum=0.25)]

def learn_style(references: list[str], slug: str, name: str,
                base: str = "energetic-event", threshold: float = 0.35) -> tuple[Style, dict]:
    if not references:
        raise ValueError("Provide at least one reference video")
    baseline = PRESETS[base]
    lengths = []
    per_video = []
    for reference in references:
        path = Path(reference)
        if not path.is_file():
            raise FileNotFoundError(reference)
        clips = scan(str(path.parent))
        info = next((item for item in clips if Path(item["path"]).resolve() == path.resolve()), None)
        if info is None or info["duration"] <= 0:
            raise ValueError(f"Cannot inspect video: {reference}")
        cuts = detect_cuts(str(path), threshold=threshold)
        sample = estimate_cut_lengths(info["duration"], cuts)
        lengths.extend(sample)
        per_video.append({"name": path.name, "duration_seconds": info["duration"],
                          "candidate_cuts": len(cuts), "median_segment_seconds": round(median(sample), 3) if sample else None})
    pace = max(0.25, min(15.0, median(lengths)))
    style = replace(baseline, slug=slug, name=name, cut_seconds=round(pace, 3),
                    description=f"Cutting pace estimated from {len(references)} reference video(s); other settings inherited from {baseline.name}",
                    source="reference-analysis").validate()
    return style, {"videos": per_video, "estimated_cut_seconds": style.cut_seconds,
                   "limitations": ["Cuts are candidates, not manually verified edits",
                                   "Music sync, speed ramps and colour are not learned yet",
                                   "Other controls are inherited from the selected preset"]}
