"""Editable title specifications and FFmpeg drawtext animation expressions."""
from math import isfinite
from pathlib import Path

POSITIONS = {
    "top-left": (0.08, 0.12), "top": (0.5, 0.12), "top-right": (0.92, 0.12),
    "left": (0.08, 0.5), "center": (0.5, 0.5), "right": (0.92, 0.5),
    "bottom-left": (0.08, 0.88), "bottom": (0.5, 0.88), "bottom-right": (0.92, 0.88),
}
ANIMATIONS = {"none", "fade", "zoom", "slide-left", "slide-right", "pop"}

def number(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return float(value)

def validate_titles(titles, duration):
    if not isinstance(titles, list):
        raise ValueError("Titles must be a list")
    result = []
    for title in titles:
        if not isinstance(title, dict):
            raise ValueError("Title must be an object")
        text = title.get("text")
        if not isinstance(text, str) or not text.strip() or len(text) > 250:
            raise ValueError("Title text must be 1-250 characters")
        start = number(title.get("start"), "start", 0, duration)
        end = number(title.get("end"), "end", 0, duration)
        if end <= start:
            raise ValueError("Title end must follow start")
        position = title.get("position", "bottom")
        animation = title.get("animation", "fade")
        if position not in POSITIONS or animation not in ANIMATIONS:
            raise ValueError("Unsupported title position or animation")
        px, py = POSITIONS[position]
        x = number(title.get("x", px * 100), "x", 0, 100)
        y = number(title.get("y", py * 100), "y", 0, 100)
        size = title.get("size", 44)
        if isinstance(size, bool) or not isinstance(size, int) or not 12 <= size <= 120:
            raise ValueError("Title size must be 12-120")
        color = title.get("color", "white")
        if not isinstance(color, str) or not (color in ("white", "black", "gold") or
            (len(color) == 7 and color[0] == "#" and all(c in "0123456789abcdefABCDEF" for c in color[1:]))):
            raise ValueError("Unsupported title color")
        opacity = number(title.get("opacity", 100), "opacity", 0, 100)
        duration_in = number(title.get("animation_duration", 0.4), "animation_duration", 0.05, 10)
        duration_in = min(duration_in, (end - start) / 2)
        result.append({"text": text, "start": start, "end": end, "position": position,
                       "x": x, "y": y, "animation": animation, "size": size,
                       "color": color, "opacity": opacity,
                       "animation_duration": duration_in,
                       "locked": bool(title.get("locked", False))})
    return result

def filter_chain(titles, directory, duration):
    filters = []
    for i, title in enumerate(validate_titles(titles, duration)):
        textfile = Path(directory) / f"title-{i}.txt"
        textfile.write_text(title["text"], encoding="utf-8")
        color = "0xD4AF37" if title["color"] == "gold" else title["color"].replace("#", "0x")
        start, end, d = title["start"], title["end"], title["animation_duration"]
        progress = f"min(1,max(0,(t-{start})/{d}))"
        x = f"(w-text_w)*{title['x']/100}"
        y = f"(h-text_h)*{title['y']/100}"
        alpha = str(title["opacity"] / 100)
        animation = title["animation"]
        if animation == "fade":
            alpha = f"({alpha})*min({progress},max(0,({end}-t)/{d}))"
        elif animation == "slide-left":
            x = f"({x})+(w*0.2)*(1-{progress})"
        elif animation == "slide-right":
            x = f"({x})-(w*0.2)*(1-{progress})"
        elif animation == "zoom":
            size = f"{title['size']}*(0.75+0.25*{progress})"
        elif animation == "pop":
            size = f"{title['size']}*(1+0.18*(1-{progress}))"
        else:
            size = str(title["size"])
        if animation not in ("zoom", "pop"):
            size = str(title["size"])
        filters.append(
            f"drawtext=textfile='{textfile.as_posix()}':fontcolor={color}:fontsize='{size}'"
            f":x='{x}':y='{y}':alpha='{alpha}':enable='between(t,{start},{end})'")
    return ",".join(filters)
