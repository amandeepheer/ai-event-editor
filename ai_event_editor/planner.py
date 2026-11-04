"""Frame-based event recap planning from whatever reviewed footage is available."""
from collections import deque
from dataclasses import dataclass
from math import isfinite
from typing import Any
from .beat_sync import beat_frames, choose_cut
from .speed_effects import speed_effect

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
    id: str | None = None
    must_include: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Shot":
        allowed = cls.__dataclass_fields__
        shot = cls(**{key: data[key] for key in allowed if key in data})
        numbers = (shot.start, shot.end, shot.quality, shot.fps)
        if (not all(isinstance(x, (int, float)) and not isinstance(x, bool) and isfinite(x) for x in numbers)
                or shot.category not in ORDER or not isinstance(shot.path, str) or not shot.path.strip()
                or shot.start < 0 or shot.end <= shot.start or not 0 <= shot.quality <= 1 or shot.fps <= 0
                or not isinstance(shot.must_include, bool)
                or (shot.id is not None and (not isinstance(shot.id, str) or not shot.id))):
            raise ValueError("Invalid shot data")
        return shot


def _allocate(total, weights, capacities, minimums):
    """Bounded weighted allocation; absent/short categories donate their share."""
    if sum(capacities) < total:
        raise ValueError(f"Insufficient unique footage: need {total/FPS:g}s, have {sum(capacities)/FPS:g}s")
    if sum(minimums) > total:
        raise ValueError("Too many Must include moments for this duration; choose a longer edit or unpin shots")
    values = list(minimums)
    while sum(values) < total:
        active = [i for i in range(len(weights)) if values[i] < capacities[i]]
        remaining = total - sum(values)
        weight = sum(weights[i] for i in active)
        extra = {i: min(capacities[i]-values[i], int(remaining*weights[i]/weight)) for i in active}
        if not any(extra.values()):
            for i in sorted(active, key=lambda i: (-weights[i], i))[:remaining]:
                extra[i] = 1
        for i, frames in extra.items():
            values[i] += frames
    return values


def plan(shots: list[Shot], beats: list[float], duration: int = 60, style=None, mix=None,
         section_energy: dict[str, int] | None = None, auto_speed: bool = False,
         music_energy: list[dict] | None = None) -> dict[str, Any]:
    if isinstance(duration, bool) or not isinstance(duration, int) or not MIN_DURATION <= duration <= MAX_DURATION:
        raise ValueError("Duration must be an integer from 30 to 300 seconds")
    shots = [Shot.from_dict(vars(s)) for s in shots]
    if not shots:
        raise ValueError("No kept footage. Keep at least one shot before creating an edit")
    if section_energy is not None:
        if mix is None:
            raise ValueError("Section energy requires dynamic mix")
        if not isinstance(section_energy, dict) or any(k not in ORDER or isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 100 for k, v in section_energy.items()):
            raise ValueError("Section energy must map valid categories to integers 0-100")
    if music_energy is not None and (not isinstance(music_energy, list) or any(
        not isinstance(e, dict) or not all(isinstance(e.get(k), (int, float)) and not isinstance(e.get(k), bool) and isfinite(e[k]) for k in ('time', 'energy'))
        or e['time'] < 0 or not 0 <= e['energy'] <= 1 for e in music_energy)):
        raise ValueError("Invalid music energy envelope")
    if style is not None:
        style.validate()
    if mix is not None:
        mix.validate()
    # Protect pinned moments first; never reuse overlapping source ranges.
    unique, ranges = [], {}
    for shot in sorted(shots, key=lambda s: (not s.must_include, -s.quality, s.path, s.start)):
        if any(shot.start < end and start < shot.end for start, end in ranges.get(shot.path, [])):
            if shot.must_include:
                raise ValueError("Must include moments overlap; adjust their source ranges")
            continue
        ranges.setdefault(shot.path, []).append((shot.start, shot.end))
        unique.append(shot)
    target_frames = duration * FPS
    beats_in_frames = beat_frames(beats, FPS, target_frames)
    if mix is not None:
        from dataclasses import replace
        from .dynamic_mix import assign_styles
        styles = [assign_styles(replace(mix, energy=(section_energy or {}).get(cat, mix.energy)), (cat,), beats, duration)[0] for cat in ORDER]
    else:
        styles = [style] * len(ORDER)
    targets = [max(FPS//2, round(s.cut_seconds*FPS)) if s else (4 if cat in ('drone', 'finale') else 3)*FPS for cat, s in zip(ORDER, styles)]
    grouped = [[s for s in unique if s.category == cat] for cat in ORDER]
    capacity = [sum(int((s.end-s.start)*FPS+1e-7) for s in group) for group in grouped]
    minimum = [sum(min(int((s.end-s.start)*FPS+1e-7), target) for s in group if s.must_include) for group, target in zip(grouped, targets)]
    weights = style.category_weights if style else WEIGHTS
    allocation = _allocate(target_frames, weights, capacity, minimum)
    segments, position = [], 0
    for index, (category, group, remaining) in enumerate(zip(ORDER, grouped, allocation)):
        # Rank moments within each source, but rotate sources at every cut. A long
        # file with many equally ranked windows must not crowd out other cameras.
        pending, pinned = {}, deque()
        for shot in group:
            available = int((shot.end-shot.start)*FPS+1e-7)
            if available < 1:
                continue
            queue = pending.setdefault(shot.path, deque())
            entry = (shot, shot.start, available)
            (pinned if shot.must_include else queue).append(entry)
        sources = deque(pending)
        reserve = sum(min(cap, targets[index]) for _, _, cap in pinned)
        while remaining:
            if pinned:
                shot, source, available = pinned.popleft()
                reserve -= min(available, targets[index])
            else:
                while not pending[sources[0]]:
                    sources.popleft()
                path = sources[0]
                sources.rotate(-1)
                shot, source, available = pending[path].popleft()
            energy = (section_energy or {}).get(category, mix.energy if mix else 50)
            target = targets[index]
            if music_energy:
                nearest = min(music_energy, key=lambda e: abs(e['time']-position/FPS))
                # More movement in louder music passages, without changing effect frequency.
                target = max(FPS//2, round(target*(1.3-0.6*nearest['energy'])))
            # Reserve a useful excerpt for each still-pending pinned moment.
            limit = remaining-reserve
            if shot.must_include and source == shot.start:
                target = min(targets[index], available)
            frames = choose_cut(position, limit, available, target, beats_in_frames, FPS, energy) if beats_in_frames else min(limit, available, target)
            if frames < 1:
                raise ValueError("Must include moments cannot fit this edit; increase duration")
            effect = speed_effect(category, shot.fps, energy, FPS) if auto_speed else {"kind": "normal", "speed": 1.0, "requires_render": False}
            segments.append({"id": f"clip-{len(segments)+1:05d}", "shot_id": shot.id,
                "must_include": shot.must_include, "path": shot.path, "category": category,
                "source_in_seconds": source, "source_end_seconds": shot.end,
                "source_in_frame": round(source*FPS), "source_fps": shot.fps,
                "timeline_start": position, "duration_frames": frames, "speed": 1.0,
                "speed_effect": effect, "edit_style": styles[index].slug if styles[index] else None})
            remaining -= frames
            position += frames
            if available > frames:
                pending[shot.path].append((shot, source+frames/FPS, available-frames))
    missing = [c for c, cap in zip(ORDER, capacity) if not cap]
    from .edit_plan import validate_plan
    return validate_plan({"schema_version": 1, "fps": FPS, "duration_seconds": duration,
        "duration_frames": target_frames, "style": style.slug if style else None,
        "dynamic_mix": mix.to_dict() if mix else None, "section_energy": section_energy or {},
        "segments": segments, "missing_categories": missing,
        "warnings": (["Missing coverage: " + ', '.join(missing)] if missing else []) +
            (["Edit uses " + str(len({s['path'] for s in segments})) + " of " +
              str(len({s.path for s in unique})) + " eligible source videos; duration, category allocation and Must include choices can limit coverage."]
             if {s['path'] for s in segments} != {s.path for s in unique} else []) + [
            "Shot categories and quality scores require human review",
            "Speed effects remain planning metadata; native Premiere compatibility requires host testing"]})
