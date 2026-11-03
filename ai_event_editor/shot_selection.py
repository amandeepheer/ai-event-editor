"""Deterministic candidate ranking and simple semantic-label suggestions.

Labels require confirmation; a generic image embedding model is not
guaranteed to recognize event-specific performers or important guests.
"""
from collections import defaultdict

LABELS = ("drone", "stalls", "performance", "dancing", "crowd", "finale")

def rank_candidates(candidates: list[dict], min_confidence: float = 0.35) -> dict[str, list[dict]]:
    ranked = defaultdict(list)
    for candidate in candidates:
        label = candidate.get("category")
        confidence = float(candidate.get("confidence", 1.0))
        if label not in LABELS or confidence < min_confidence:
            continue
        duration = float(candidate.get("end", 0)) - float(candidate.get("start", 0))
        if duration < 0.5:
            continue
        quality = max(0.0, min(1.0, float(candidate.get("quality", 0.5))))
        score = 0.7 * quality + 0.3 * confidence
        ranked[label].append({**candidate, "selection_score": round(score, 4)})
    return {label: sorted(items, key=lambda c: (-c["selection_score"], c["path"], c["start"]))
            for label, items in ranked.items()}

def coverage_report(candidates: list[dict]) -> dict:
    ranked = rank_candidates(candidates)
    missing = [label for label in LABELS if not ranked.get(label)]
    return {"missing_categories": missing, "counts": {label: len(ranked.get(label, [])) for label in LABELS},
            "ready_for_planning": not missing}
