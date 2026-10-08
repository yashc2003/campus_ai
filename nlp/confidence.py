from __future__ import annotations


def confidence_band(score: float, high: float = .85, medium: float = .60) -> str:
    if score >= high:
        return "High confidence"
    if score >= medium:
        return "Needs review"
    return "Low confidence"
