"""Duration-adjustable, frame-based event recap planner."""
from dataclasses import dataclass
from typing import Any

FPS = 25
MIN_DURATION = 30
MAX_DURATION = 300
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
    if isinstance(duration, bool) or not isinstance(duration, int) or not MIN_DURATION <= duration <= MAX_DURATION:
        raise ValueError("Duration must be an integer from 30 to 300 seconds")
    for category in ORDER:
        if not any(s.category == category for s in shots):
            raise ValueError(f"Missing required category: {category}")
    target_frames = duration * FPS
    beat_frames = sorted({round(t * FPS) for t in beats if 0 < t < duration})
    # Largest remainder allocation preserves exact frame count for any duration.
    raw = [target_frames * w / sum(WEIGHTS) for w in WEIGHTS]
    allocation = [int(x) for x in raw]
    for index in sorted(range(len(raw)), key=lambda i: (-(raw[i] - allocation[i]), i))[:target_frames - sum(allocation)]:
        allocation[index] += 1
    bounds = [0]
    cursor = 0
    for frames in allocation[:-1]:
        cursor += frames
        nearby = [b for b in beat_frames if abs(b - cursor) <= 12 and b > bounds[-1] + FPS]
        bounds.append(min(nearby, key=lambda b: abs(b - cursor)) if nearby else cursor)
    bounds.append(target_frames)
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
    assert sum(s["duration_frames"] for s in segments) == target_frames
    return {"fps": FPS, "duration_seconds": duration, "duration_frames": target_frames, "segments": segments, "warnings": ["Shot categories are model suggestions or manually supplied", "Premiere import and non-25fps sources are not validated"]}
