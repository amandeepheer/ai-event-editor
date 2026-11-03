"""Turn AI frame observations into ranked, non-overlapping usable shots.

Scores are heuristic suggestions, not guarantees of photographic quality.
No original video is modified.
"""
from __future__ import annotations
from collections import defaultdict
from math import isfinite

CATEGORIES = ("drone", "stalls", "performance", "dancing", "crowd", "finale")

def select_shots(candidates: list[dict], min_confidence: float = 0.0,
                 min_length: float = 0.5, max_per_category: int | None = None) -> list[dict]:
    if not 0 <= min_confidence <= 1 or not isfinite(min_confidence):
        raise ValueError("min_confidence must be between 0 and 1")
    if min_length <= 0 or not isfinite(min_length):
        raise ValueError("min_length must be positive")
    if max_per_category is not None and (isinstance(max_per_category, bool) or max_per_category < 1):
        raise ValueError("max_per_category must be positive")
    grouped = defaultdict(list)
    for candidate in candidates:
        try:
            category = candidate["category"]
            path = candidate["path"]
            start, end = float(candidate["start"]), float(candidate["end"])
            confidence = float(candidate.get("confidence", 0))
            quality = float(candidate.get("quality", 0.5))
        except (KeyError, TypeError, ValueError):
            continue
        if (category not in CATEGORIES or not isinstance(path, str) or not path
                or not all(map(isfinite, (start, end, confidence, quality)))
                or start < 0 or end - start < min_length
                or not 0 <= confidence <= 1 or not 0 <= quality <= 1
                or confidence < min_confidence):
            continue
        # CLIP probabilities are relative to supplied prompts; don't interpret
        # them as calibrated certainty. Prioritise quality, then model score.
        score = round(0.65 * quality + 0.35 * confidence, 6)
        grouped[category].append({**candidate, "start": start, "end": end,
                                  "quality": quality, "selection_score": score})
    chosen = []
    # Global overlap protection prevents the same footage from appearing in
    # two categories and avoids redundant overlapping frame samples.
    used = defaultdict(list)
    all_candidates = sorted((c for items in grouped.values() for c in items),
                            key=lambda c: (-c["selection_score"], c["path"], c["start"], c["category"]))
    counts = defaultdict(int)
    for candidate in all_candidates:
        category, path = candidate["category"], candidate["path"]
        if max_per_category is not None and counts[category] >= max_per_category:
            continue
        if any(candidate["start"] < end and start < candidate["end"] for start, end in used[path]):
            continue
        used[path].append((candidate["start"], candidate["end"]))
        counts[category] += 1
        chosen.append(candidate)
    return sorted(chosen, key=lambda c: (CATEGORIES.index(c["category"]), -c["selection_score"], c["path"], c["start"]))

def selection_report(shots: list[dict]) -> dict:
    counts = {category: sum(s["category"] == category for s in shots) for category in CATEGORIES}
    missing = [category for category, count in counts.items() if count == 0]
    return {"selected": len(shots), "counts": counts, "missing_categories": missing,
            "ready_for_current_planner": not missing,
            "warning": "AI categories and heuristic quality scores require human review"}
