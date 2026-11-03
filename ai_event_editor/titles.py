"""Editable title specification for FFmpeg overlays."""
from math import isfinite

POSITIONS = {"top": "(h*0.14)", "center": "(h-text_h)/2", "bottom": "(h*0.82-text_h)"}
ANIMATIONS = {"none", "fade"}

def validate_titles(titles, duration):
    if not isinstance(titles, list):
        raise ValueError("Titles must be a list")
    result = []
    for title in titles:
        if not isinstance(title, dict):
            raise ValueError("Title must be an object")
        text = title.get("text")
        start = title.get("start")
        end = title.get("end")
        if not isinstance(text, str) or not text.strip() or len(text) > 250:
            raise ValueError("Title text must be 1-250 characters")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) for v in (start, end)):
            raise ValueError("Title times must be finite numbers")
        if not 0 <= start < end <= duration:
            raise ValueError("Title must fit inside video")
        position = title.get("position", "bottom")
        animation = title.get("animation", "fade")
        if position not in POSITIONS or animation not in ANIMATIONS:
            raise ValueError("Unsupported title position or animation")
        size = title.get("size", 44)
        if isinstance(size, bool) or not isinstance(size, int) or not 12 <= size <= 120:
            raise ValueError("Title size must be 12-120")
        color = title.get("color", "white")
        if not isinstance(color, str) or not (color in ("white", "black", "gold") or
            (len(color) == 7 and color[0] == "#" and all(c in "0123456789abcdefABCDEF" for c in color[1:]))):
            raise ValueError("Unsupported title color")
        result.append({"text": text, "start": float(start), "end": float(end),
                       "position": position, "animation": animation, "size": size, "color": color})
    return result

def filter_chain(titles, directory, duration):
    """Create text files to avoid FFmpeg filter-escaping user text."""
    from pathlib import Path
    filters = []
    for i, title in enumerate(validate_titles(titles, duration)):
        textfile = Path(directory) / f"title-{i}.txt"
        textfile.write_text(title["text"], encoding="utf-8")
        color = "0xD4AF37" if title["color"] == "gold" else title["color"].replace("#", "0x")
        start, end = title["start"], title["end"]
        alpha = "1"
        if title["animation"] == "fade":
            fade = min(0.4, (end - start) / 3)
            alpha = f"min(1,max(0,(t-{start})/{fade}),max(0,({end}-t)/{fade}))"
        # Text file path is created inside our temporary directory.
        filters.append(
            f"drawtext=textfile='{textfile.as_posix()}':fontcolor={color}:fontsize={title['size']}"
            f":x=(w-text_w)/2:y={POSITIONS[title['position']]}"
            f":alpha='{alpha}':enable='between(t,{start},{end})'")
    return ",".join(filters)
