from __future__ import annotations

from datetime import datetime, timezone
import secrets

from pymongo.database import Database


def record_query(database: Database, query: str, prediction: dict, language: str,
                 retrieved: list[dict], answer: str, answer_found: bool | None = None,
                 student_id: str | None = None) -> str:
    query_id = secrets.token_hex(10)
    verified = bool(retrieved) if answer_found is None else answer_found
    database["queries"].insert_one({"query_id": query_id, "query": query,
        "predicted_intent": prediction.get("intent"), "confidence": prediction.get("confidence"),
        "model_version": prediction.get("model_version"), "language": language,
        "source": retrieved[0].get("filename") if retrieved and verified else None,
        "source_page": retrieved[0].get("page") if retrieved and verified else None,
        "answer_found": verified, "status": "answered" if verified else "unresolved",
        "student_id": student_id, "timestamp": datetime.now(timezone.utc), "feedback": None})
    return query_id


def record_feedback(database: Database, query_id: str, helpful: bool,
                    corrected_intent: str | None = None) -> None:
    database["feedback"].insert_one({"query_id": query_id, "helpful": helpful,
        "corrected_intent": corrected_intent, "review_status": "pending" if corrected_intent else "new",
        "created_at": datetime.now(timezone.utc)})
    database["queries"].update_one({"query_id": query_id}, {"$set": {"feedback": helpful}})
