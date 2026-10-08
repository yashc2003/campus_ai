from __future__ import annotations

from datetime import datetime, timezone
import secrets

from pymongo.database import Database


def ticket_priority(query: str, intent: str | None) -> str:
    text = f"{query} {intent or ''}".casefold()
    urgent = ("urgent", "deadline", "last date", "exam", "examination", "fee", "fees", "payment")
    if any(term in text for term in urgent): return "High"
    if not intent or intent.casefold() in {"general / other", "general", "other"}: return "Low"
    return "Medium"


def create_ticket(database: Database, query: str, intent: str | None,
                  confidence: float | None, student_name: str = "",
                  student_id: str | None = None) -> str:
    ticket_id = "CA-" + secrets.token_hex(8).upper()
    department = intent or "General / Other"
    database["tickets"].insert_one({"ticket_id": ticket_id,
        "student_id": student_id, "student_name": student_name.strip()[:80] or None, "query": query.strip()[:3000],
        "predicted_intent": intent, "confidence": confidence, "department": department,
        "priority": ticket_priority(query, intent), "status": "Open", "assigned_staff": None,
        "resolution": None, "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)})
    return ticket_id


def update_ticket(database: Database, ticket_id: str, status: str, resolution: str = "",
                  assigned_staff: str | None = None) -> bool:
    allowed = {"Open", "Assigned", "In Progress", "Resolved", "Closed"}
    if status not in allowed:
        raise ValueError("Invalid ticket status.")
    result = database["tickets"].update_one({"ticket_id": ticket_id}, {"$set": {
        "status": status, "resolution": resolution.strip()[:2000] or None,
        "assigned_staff": assigned_staff.strip()[:120] if assigned_staff and assigned_staff.strip() else None,
        "updated_at": datetime.now(timezone.utc)}})
    return result.matched_count > 0
