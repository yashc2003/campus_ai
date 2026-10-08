from __future__ import annotations
from functools import lru_cache
import os

from rag.retriever import sparse_embedding, VECTOR_DIMENSIONS

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

@lru_cache(maxsize=1)
def _local_sentence_encoder():
    try:
        from huggingface_hub import snapshot_download
        from sentence_transformers import SentenceTransformer
        path = snapshot_download(os.getenv("RAG_EMBEDDING_MODEL", DEFAULT_MODEL), local_files_only=True)
        return SentenceTransformer(path, device="cpu")
    except Exception:
        return None

def encode_text(text: str) -> tuple[str, list[int], list[float]]:
    """Use a locally cached multilingual sentence model; fall back to stable sparse vectors."""
    encoder = _local_sentence_encoder()
    if encoder is not None:
        vector = encoder.encode([text], normalize_embeddings=True)[0].tolist()
        model_name = os.getenv("RAG_EMBEDDING_MODEL", DEFAULT_MODEL)
        return f"sentence-transformers:{model_name}", list(range(len(vector))), vector
    indices, values = sparse_embedding(text)
    return f"hashing-char-ngrams:{VECTOR_DIMENSIONS}", indices, values

def encode_query(text: str, model_tag: str) -> tuple[list[int], list[float]]:
    if model_tag.startswith("sentence-transformers:"):
        encoder = _local_sentence_encoder()
        if encoder is None:
            return [], []
        vector = encoder.encode([text], normalize_embeddings=True)[0].tolist()
        return list(range(len(vector))), vector
    return sparse_embedding(text)
