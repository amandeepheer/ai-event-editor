"""Non-destructive speed-effect suggestions for a future renderer.

A speed envelope is metadata only; no retiming is applied by the XML exporter.
"""
from math import isfinite

def speed_effect(category, source_fps, energy, timeline_fps=25):
    if (isinstance(energy, bool) or not isinstance(energy, int)
            or not 0 <= energy <= 100):
        raise ValueError("Energy must be an integer between 0 and 100")
    if (isinstance(source_fps, bool) or not isinstance(source_fps, (int, float))
            or not isfinite(source_fps) or source_fps <= 0):
        raise ValueError("Source fps must be finite and positive")
    if (isinstance(timeline_fps, bool) or not isinstance(timeline_fps, (int, float))
            or not isfinite(timeline_fps) or timeline_fps <= 0):
        raise ValueError("Timeline fps must be finite and positive")
    slow = min(1.0, timeline_fps / source_fps)
    if category in ("performance", "dancing", "finale") and energy >= 65 and slow < 1:
        if energy >= 85 and category in ("dancing", "finale"):
            return {"kind": "ramp", "speed": 1.0,
                    "keyframes": [{"at": 0.0, "speed": 1.0},
                                  {"at": 0.4, "speed": slow},
                                  {"at": 0.7, "speed": slow},
                                  {"at": 1.0, "speed": 1.0}],
                    "requires_render": True}
        return {"kind": "slow_motion", "speed": slow, "requires_render": True}
    return {"kind": "normal", "speed": 1.0, "requires_render": False}
