"""Plan speed effects without modifying original footage."""

def speed_effect(category, source_fps, energy, timeline_fps=25):
    if not 0 <= energy <= 100 or source_fps <= 0:
        raise ValueError("Invalid energy or frame rate")
    slow = min(1.0, timeline_fps / source_fps)
    if category in ("performance", "dancing", "finale") and energy >= 65 and slow < 1:
        if energy >= 85 and category in ("dancing", "finale"):
            return {"kind": "ramp", "speed": 1.0, "keyframes": [{"at": 0, "speed": 1}, {"at": 0.4, "speed": slow}, {"at": 0.7, "speed": slow}, {"at": 1, "speed": 1}], "requires_render": True}
        return {"kind": "slow_motion", "speed": slow, "requires_render": True}
    return {"kind": "normal", "speed": 1.0, "requires_render": False}
