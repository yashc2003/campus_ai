from __future__ import annotations

import re
from functools import lru_cache
from sklearn.feature_extraction.text import HashingVectorizer

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

VECTOR_DIMENSIONS = 2 ** 14

@lru_cache(maxsize=1)
def _hashing_vectorizer():
    return HashingVectorizer(analyzer="char", ngram_range=(2, 5), n_features=VECTOR_DIMENSIONS,
                             norm="l2", alternate_sign=False, lowercase=True)

def sparse_embedding(text: str) -> tuple[list[int], list[float]]:
    """A deterministic, multilingual-friendly character n-gram vector (no model download)."""
    row = _hashing_vectorizer().transform([text])
    return row.indices.astype(int).tolist(), row.data.astype(float).tolist()


def retrieve(query: str, chunks: list[dict], limit: int = 4) -> list[dict]:
    usable = [chunk for chunk in chunks if str(chunk.get("text", "")).strip()]
    if not usable or not query.strip():
        return []
    from rag.embeddings import encode_query
    query_vectors = {}
    scores = []
    for chunk in usable:
        if "vector_indices" in chunk and "vector_values" in chunk:
            model_tag = chunk.get("embedding_model", f"hashing-char-ngrams:{VECTOR_DIMENSIONS}")
            if model_tag not in query_vectors:
                query_vectors[model_tag] = encode_query(query, model_tag)
            query_indices, query_values = query_vectors[model_tag]
            if not query_indices:
                scores.append(0.0)
                continue
            query_vector = dict(zip(query_indices, query_values))
            vector = dict(zip(chunk["vector_indices"], chunk["vector_values"]))
            score = sum(value * vector.get(index, 0.0) for index, value in query_vector.items())
        else:
            try:
                matrix = TfidfVectorizer(ngram_range=(1, 2), stop_words="english").fit_transform([query, str(chunk["text"])])
                score = float(cosine_similarity(matrix[0:1], matrix[1:]).ravel()[0])
            except ValueError:
                score = 0.0
        scores.append(score)
    ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)
    internal = {"vector_indices", "vector_values", "embedding_model"}
    return [{**{key: value for key, value in usable[index].items() if key not in internal},
             "relevance": float(score)} for index, score in ranked[:limit] if score > 0]


def evidence_excerpt(text: str, query: str, window: int = 480) -> str:
    body = re.sub(r"\s+", " ", text).strip()
    if len(body) <= window:
        return body
    tokens = {term.casefold() for term in re.findall(r"\w+", query) if len(term) > 2}
    lower = body.casefold()
    offsets = [lower.find(term) for term in tokens if lower.find(term) >= 0]
    start = max(0, (min(offsets) if offsets else 0) - window // 4)
    return ("…" if start else "") + body[start:start + window].rstrip() + ("…" if start + window < len(body) else "")
