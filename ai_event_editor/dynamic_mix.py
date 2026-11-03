"""Deterministic section-aware dynamic style mixing (no claims of AI scene understanding)."""
from dataclasses import asdict, dataclass
from .styles import PRESETS, Style

ALIASES = {"cinematic": "cinematic", "energetic": "energetic-event",
           "fast-cuts": "social-reel", "emotional": "wedding"}

@dataclass(frozen=True)
class DynamicMix:
    mode: str = "auto"
    selected: tuple[str, ...] = ("cinematic", "energetic", "fast-cuts", "emotional")
    energy: int = 75

    def validate(self):
        if self.mode != "auto":
            raise ValueError("Only auto mixing is supported")
        if isinstance(self.energy, bool) or not isinstance(self.energy, int) or not 0 <= self.energy <= 100:
            raise ValueError("Energy must be 0-100")
        if not self.selected or len(set(self.selected)) != len(self.selected) or any(x not in ALIASES for x in self.selected):
            raise ValueError("Select one or more unique supported styles")
        return self

    def to_dict(self):
        data = asdict(self)
        data["selected"] = list(self.selected)
        return data

def assign_styles(mix: DynamicMix, categories, beats, duration) -> list[Style]:
    """Assign a different profile per story section.

    Beat density is used only as a coarse signal. There is no semantic
    emotion detection, audio-energy analysis or learned edit decision yet.
    """
    mix.validate()
    preferred = {
        "drone": ("cinematic", "energetic"),
        "stalls": ("energetic", "cinematic"),
        "performance": ("fast-cuts", "energetic"),
        "dancing": ("fast-cuts", "energetic"),
        "crowd": ("emotional", "cinematic"),
        "finale": ("energetic", "fast-cuts"),
    }
    high = mix.energy >= 60
    result = []
    for category in categories:
        choices = preferred.get(category, ("energetic", "cinematic"))
        if not high:
            choices = tuple(reversed(choices))
        chosen = next((key for key in choices if key in mix.selected), None)
        if chosen is None:
            chosen = mix.selected[0]
        base = PRESETS[ALIASES[chosen]]
        # High energy shortens each section's average cut target, while
        # keeping slower cinematic/emotional passages distinct.
        factor = 1.15 - 0.003 * mix.energy
        from dataclasses import replace
        result.append(replace(base, cut_seconds=max(0.25, base.cut_seconds * factor)))
    return result
