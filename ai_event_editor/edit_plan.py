"""Versioned local edit-plan contract used by planning and rendering.

Legacy unversioned plans are normalized without mutating the caller. Source
seconds are authoritative; legacy source_in_frame is in TIMELINE frames.
"""
from copy import deepcopy
from math import isfinite

SCHEMA_VERSION = 1


def _number(value, name, minimum=0, positive=False, integer=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not isfinite(value) or value < minimum
            or (positive and value <= 0) or (integer and int(value) != value)):
        raise ValueError(f"{name} must be a finite {'positive' if positive else 'nonnegative'} {'integer' if integer else 'number'}")
    return int(value) if integer else value


def validate_plan(value):
    """Return a normalized copy; reject gaps, overlaps and ambiguous timing."""
    if not isinstance(value, dict):
        raise ValueError("Plan must be an object")
    plan = deepcopy(value)
    version = plan.get("schema_version", SCHEMA_VERSION)
    if isinstance(version, bool) or not isinstance(version, (int, float)) or version != SCHEMA_VERSION:
        raise ValueError("Unsupported edit-plan schema_version")
    legacy = "schema_version" not in plan
    fps = _number(plan.get("fps"), "fps", positive=True)
    total = _number(plan.get("duration_frames"), "duration_frames", positive=True, integer=True)
    segments = plan.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("Plan must contain nonempty segments")
    cursor, ids = 0, set()
    for index, segment in enumerate(segments):
        label = f"segments[{index}]"
        if not isinstance(segment, dict):
            raise ValueError(f"{label} must be an object")
        path = segment.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ValueError(f"{label}.path must be a nonempty string")
        identifier = segment.setdefault("id", f"clip-{index + 1:05d}")
        if not isinstance(identifier, str) or not identifier or identifier in ids:
            raise ValueError(f"{label}.id must be nonempty and unique")
        ids.add(identifier)
        start = segment.get("timeline_start", cursor if legacy else None)
        _number(start, f"{label}.timeline_start", integer=True)
        if start != cursor:
            raise ValueError(f"{label}: timeline must be contiguous (no gaps or overlaps)")
        length = _number(segment.get("duration_frames"), f"{label}.duration_frames", positive=True, integer=True)
        source_frame = segment.get("source_in_frame")
        if source_frame is not None:
            _number(source_frame, f"{label}.source_in_frame", integer=True)
        seconds = segment.get("source_in_seconds")
        if seconds is None:
            if source_frame is None:
                raise ValueError(f"{label}: source_in_seconds or source_in_frame is required")
            seconds = source_frame / fps
        _number(seconds, f"{label}.source_in_seconds")
        # Half-frame tolerance accounts for legacy rounded frame offsets.
        if source_frame is not None and abs(source_frame - seconds * fps) > 0.500001:
            raise ValueError(f"{label}: conflicting source offsets")
        if "source_fps" in segment:
            _number(segment["source_fps"], f"{label}.source_fps", positive=True)
        speed = _number(segment.get("speed", 1), f"{label}.speed", positive=True)
        effect = segment.get("speed_effect", {"kind": "normal", "speed": 1.0})
        if not isinstance(effect, dict) or effect.get("kind") not in ("normal", "slow_motion", "ramp"):
            raise ValueError(f"{label}: invalid speed_effect")
        effect_speed = _number(effect.get("speed", 1), f"{label}.speed_effect.speed", positive=True)
        if effect["kind"] == "normal" and effect_speed != 1:
            raise ValueError(f"{label}: normal speed_effect must have speed 1")
        if "source_end_seconds" in segment:
            end = _number(segment["source_end_seconds"], f"{label}.source_end_seconds")
            if end <= seconds:
                raise ValueError(f"{label}: source end must follow source start")
            if effect["kind"] == "normal" and seconds + length / fps * speed > end + 1e-7:
                raise ValueError(f"{label}: edit exceeds available source range")
        segment.update(timeline_start=start, source_in_seconds=seconds, speed=speed, speed_effect=effect)
        cursor += length
    if cursor != total:
        raise ValueError("duration_frames does not match segment total")
    if "duration_seconds" in plan:
        seconds = _number(plan["duration_seconds"], "duration_seconds", positive=True)
        if abs(seconds * fps - total) > 0.000001:
            raise ValueError("duration_seconds conflicts with duration_frames")
    if 'audio' in plan:
        audio = plan['audio']
        if not isinstance(audio, dict) or not isinstance(audio.get('path'), str) or not audio['path'].strip():
            raise ValueError('Audio must contain a local music path')
        _number(audio.get('start_seconds'), 'audio.start_seconds')
        length = _number(audio.get('duration_seconds'), 'audio.duration_seconds', positive=True)
        if abs(length*fps-total) > .000001:
            raise ValueError('Audio duration must match the timeline')
    plan.update(schema_version=SCHEMA_VERSION, duration_seconds=total / fps)
    return plan


def preflight_plan(value):
    """Summarize validity and standalone support without accessing media."""
    plan = validate_plan(value)
    unsupported = [s["id"] for s in plan["segments"]
                   if s["speed"] != 1 or s["speed_effect"]["kind"] != "normal"]
    return {"schema_version": SCHEMA_VERSION, "clips": len(plan["segments"]),
            "fps": plan["fps"], "duration_frames": plan["duration_frames"],
            "duration_seconds": plan["duration_seconds"],
            "standalone_supported": not unsupported, "unsupported_speed_clips": unsupported}
