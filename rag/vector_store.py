from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import secrets

from pymongo.database import Database

from rag.document_loader import chunk_pages
from rag.embeddings import encode_text
from rag.retriever import VECTOR_DIMENSIONS


def store_document(database: Database, filename: str, content: bytes, pages: list[dict]) -> str:
    checksum = hashlib.sha256(content).hexdigest()
    existing = database["documents"].find_one({"sha256": checksum})
    if existing:
        raise ValueError(f"This exact file is already indexed as {existing['filename']}.")
    document_id = secrets.token_hex(12)
    chunks = chunk_pages(pages)
    if not any(chunk["text"].strip() for chunk in chunks):
        raise ValueError("No searchable text could be extracted. Scanned image PDFs need OCR before indexing.")
    now = datetime.now(timezone.utc)
    records = []
    for index, item in enumerate(chunks):
        model_tag, indices, values = encode_text(item["text"])
        records.append({"document_id": document_id, "filename": filename, "page": item["page"],
            "text": item["text"], "chunk_index": index, "vector_indices": indices,
            "vector_values": values, "embedding_model": model_tag, "created_at": now})
    database["documents"].insert_one({"document_id": document_id, "filename": filename,
        "sha256": checksum, "size_bytes": len(content), "uploaded_at": now,
        "page_count": len(pages), "chunk_count": len(chunks), "active": True})
    try:
        database["document_chunks"].insert_many(records)
        database["embeddings_metadata"].insert_one({"document_id": document_id,
            "embedding_model": model_tag, "dimensions": VECTOR_DIMENSIONS if model_tag.startswith("hashing-") else len(records[0]["vector_indices"]),
            "chunk_count": len(records), "created_at": now})
    except Exception:
        database["document_chunks"].delete_many({"document_id": document_id})
        database["embeddings_metadata"].delete_one({"document_id": document_id})
        database["documents"].delete_one({"document_id": document_id})
        raise
    return document_id


def search_documents(database: Database, query: str, limit: int = 4) -> list[dict]:
    chunks = list(database["document_chunks"].aggregate([
        {"$lookup": {"from": "documents", "localField": "document_id", "foreignField": "document_id", "as": "document"}},
        {"$unwind": "$document"}, {"$match": {"document.active": True}},
        {"$project": {"_id": 0, "document_id": 1, "filename": 1, "page": 1, "text": 1,
                       "vector_indices": 1, "vector_values": 1, "embedding_model": 1}},
    ]))
    from rag.retriever import retrieve
    return retrieve(query, chunks, limit)
