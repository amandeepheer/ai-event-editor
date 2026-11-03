"""Frame-based metadata-driven timeline planner; automatic AI labels come later."""
from dataclasses import dataclass
from typing import Any
FPS = 25
TARGET_FRAMES = 1500
ORDER = ("drone", "stalls", "performance", "dancing", "crowd", "finale")
WEIGHTS = (8, 12, 15, 13, 6, 6)
@dataclass(frozen=True)
class Shot:
    path: str
    category: str
    start: float
    end: float
    quality: float = 0.8
    fps: float = 25.0
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Shot":
        shot = cls(**data)
        if shot.category not in ORDER or not shot.path or shot.start < 0 or shot.end <= shot.start or not 0 <= shot.quality <= 1 or shot.fps <= 0:
            raise ValueError("Invalid shot data")
        return shot

def plan(shots: list[Shot], beats: list[float], duration: int = 60) -> dict[str, Any]:
    if duration != 60:
        raise ValueError("MVP supports 60 seconds only")
    for category in ORDER:
        if not any(s.category == category for s in shots):
            raise ValueError(f"Missing required category: {category}")
    beat_frames = sorted({round(t * FPS) for t in beats if 0 < t < duration})
    bounds = [0]
    cursor = 0
    for weight in WEIGHTS[:-1]:
        cursor += weight * FPS
        nearby = [b for b in beat_frames if abs(b - cursor) <= 12 and b > bounds[-1] + 3 * FPS]
        bounds.append(min(nearby, key=lambda b: abs(b - cursor)) if nearby else cursor)
    bounds.append(TARGET_FRAMES)
    segments = []
    used = set()
    for index, category in enumerate(ORDER):
        remaining = bounds[index + 1] - bounds[index]
        position = bounds[index]
        choices = sorted((s for s in shots if s.category == category), key=lambda s: -s.quality)
        while remaining:
            available = [s for s in choices if (s.path, s.start, s.end) not in used]
            if not available:
                raise ValueError(f"Insufficient unique footage for {category}: missing {remaining/FPS:.2f}s")
            shot = available[0]
            used.add((shot.path, shot.start, shot.end))
            capacity = int((shot.end - shot.start) * FPS + 1e-7)
            frames = min(remaining, capacity, (4 if category in ("drone", "finale") else 3) * FPS)
            if frames < 1:
                raise ValueError("Source shot too short")
            segments.append({"path": shot.path, "category": category, "timeline_start": position, "duration_frames": frames, "source_in_frame": round(shot.start * FPS), "source_fps": shot.fps, "speed": 1.0})
            remaining -= frames
            position += frames
    assert sum(s["duration_frames"] for s in segments) == TARGET_FRAMES
    return {"fps": FPS, "duration_frames": TARGET_FRAMES, "segments": segments, "warnings": ["Shot labels are manually supplied", "Premiere import and non-25fps sources are not validated"]}
