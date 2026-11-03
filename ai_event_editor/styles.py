"""Versioned, reusable editing style profiles with no model retraining."""
from __future__ import annotations
import json
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path

SLUG = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
CATEGORIES = ("drone", "stalls", "performance", "dancing", "crowd", "finale")

@dataclass(frozen=True)
class Style:
    slug: str
    name: str
    description: str
    cut_seconds: float = 2.0
    cut_variation: float = 0.3
    beat_strength: float = 0.7
    transition: str = "cut"
    opening: str = "drone"
    ending: str = "finale"
    category_weights: tuple[float, ...] = (8, 12, 15, 13, 6, 6)
    version: int = 1
    source: str = "preset"

    def validate(self) -> "Style":
        if not SLUG.fullmatch(self.slug):
            raise ValueError("Invalid style slug")
        if not self.name.strip() or not self.description.strip():
            raise ValueError("Style needs name and description")
        if not 0.25 <= self.cut_seconds <= 15:
            raise ValueError("Cut length must be 0.25-15 seconds")
        if not 0 <= self.cut_variation <= 1 or not 0 <= self.beat_strength <= 1:
            raise ValueError("Invalid style controls")
        if self.transition not in ("cut", "dissolve", "mixed"):
            raise ValueError("Invalid transition")
        if self.opening not in CATEGORIES or self.ending not in CATEGORIES:
            raise ValueError("Invalid category")
        if len(self.category_weights) != len(CATEGORIES) or any(x <= 0 for x in self.category_weights):
            raise ValueError("Category weights must be positive")
        if self.version != 1:
            raise ValueError("Unsupported style schema version")
        return self

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Style":
        allowed = set(cls.__dataclass_fields__)
        if set(data) - allowed:
            raise ValueError("Unknown style fields")
        if "category_weights" in data:
            data = {**data, "category_weights": tuple(data["category_weights"])}
        return cls(**data).validate()

PRESETS = {
    "energetic-event": Style("energetic-event", "Energetic Event Highlights", "Fast cuts, lively event coverage", 1.4, 0.35, 0.9),
    "cinematic": Style("cinematic", "Cinematic", "Slower shots and deliberate pacing", 4.0, 0.25, 0.5, "mixed"),
    "wedding": Style("wedding", "Wedding Highlights", "Emotional moments and graceful pacing", 3.0, 0.35, 0.65, "mixed"),
    "concert": Style("concert", "Concert and Stage", "Performance-led with crowd reactions", 1.8, 0.35, 0.85),
    "social-reel": Style("social-reel", "Social Media Reel", "Quick hooks and compact shots", 0.9, 0.35, 0.95),
    "documentary": Style("documentary", "Documentary", "Longer narrative shots", 5.0, 0.2, 0.3),
}

def load_style(slug: str, directory: str | Path | None = None) -> Style:
    if not SLUG.fullmatch(slug):
        raise ValueError("Invalid style slug")
    if directory is not None:
        path = Path(directory) / (slug + ".json")
        if path.is_file():
            result = Style.from_dict(json.loads(path.read_text(encoding="utf-8")))
            if result.slug != slug:
                raise ValueError("Style slug mismatch")
            return result
    if slug in PRESETS:
        return PRESETS[slug].validate()
    raise FileNotFoundError(f"No style found: {slug}")

def save_style(style: Style, directory: str | Path) -> Path:
    style.validate()
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    path = root / (style.slug + ".json")
    path.write_text(json.dumps(style.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path

def blend_styles(primary: Style, secondary: Style, amount: float, slug: str, name: str) -> Style:
    if not 0 <= amount <= 1:
        raise ValueError("Blend amount must be 0-1")
    blend = lambda a, b: a * (1 - amount) + b * amount
    return replace(primary, slug=slug, name=name,
                   description=f"Blend of {primary.name} and {secondary.name}",
                   cut_seconds=blend(primary.cut_seconds, secondary.cut_seconds),
                   cut_variation=blend(primary.cut_variation, secondary.cut_variation),
                   beat_strength=blend(primary.beat_strength, secondary.beat_strength),
                   category_weights=tuple(blend(a, b) for a, b in zip(primary.category_weights, secondary.category_weights)),
                   transition=primary.transition if amount < 0.5 else secondary.transition,
                   opening=primary.opening if amount < 0.5 else secondary.opening,
                   ending=primary.ending if amount < 0.5 else secondary.ending,
                   source="blend").validate()
