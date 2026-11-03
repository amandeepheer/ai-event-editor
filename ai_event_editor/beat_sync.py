"""Frame-accurate beat-aware cut placement with minimum shot lengths."""
from math import isfinite

def beat_frames(beats, fps: int, duration_frames: int) -> list[int]:
    if fps <= 0 or duration_frames <= 0:
        raise ValueError("fps and duration must be positive")
    result = set()
    for value in beats:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            continue
        frame = round(value * fps)
        if 0 < frame < duration_frames:
            result.add(frame)
    return sorted(result)

def choose_cut(position: int, remaining: int, capacity: int, target: int,
               beats: list[int], fps: int, energy: int) -> int:
    """Return a legal duration, preferring nearby beats without creating tiny shots."""
    if isinstance(energy, bool) or not isinstance(energy, int) or not 0 <= energy <= 100:
        raise ValueError("energy must be 0-100")
    limit = min(remaining, capacity)
    if limit <= 0:
        raise ValueError("no usable frames")
    if limit <= max(1, round(fps * 0.5)):
        return limit
    ideal = min(limit, max(1, target))
    # Avoid creating a near-zero remainder if the current source can absorb it.
    if remaining > ideal and remaining - ideal < round(fps * 0.5) and capacity >= remaining:
        return remaining
    min_length = min(limit, max(1, round(fps * (0.55 if energy >= 70 else 0.85))))
    # At low energy, respect a tighter snapping tolerance to retain long takes.
    tolerance = round(fps * (0.18 + 0.0025 * energy))
    nearby = [b - position for b in beats if min_length <= b - position <= limit
              and abs((b - position) - ideal) <= tolerance]
    if nearby:
        return min(nearby, key=lambda d: (abs(d - ideal), d))
    return ideal
