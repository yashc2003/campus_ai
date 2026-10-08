from __future__ import annotations


def verified_answer(retrieved: list[dict], min_relevance: float = .08) -> dict:
    """Extractive answer only: every displayed claim remains in cited source text."""
    if not retrieved or retrieved[0]["relevance"] < min_relevance:
        return {"found": False, "answer": "I couldn't find a verified answer in the available college documents.", "sources": []}
    sources = [item for item in retrieved if item["relevance"] >= min_relevance]
    return {"found": True, "answer": sources[0]["text"], "sources": sources}
