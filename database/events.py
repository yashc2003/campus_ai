from __future__ import annotations

from datetime import datetime, timezone
import secrets
import hashlib

from pymongo.database import Database


def upsert_event(database: Database, title: str, event_date: datetime, category: str,
                 description: str, event_id: str | None = None) -> str:
    if not title.strip():
        raise ValueError("Event title is required.")
    identifier = event_id or "EV-" + secrets.token_hex(5).upper()
    database["calendar_events"].update_one({"event_id": identifier}, {"$set": {
        "event_id": identifier, "title": title.strip()[:160], "event_date": event_date,
        "category": category, "description": description.strip()[:2000],
        "updated_at": datetime.now(timezone.utc)}}, upsert=True)
    return identifier


def publish_notice_notification(database: Database, title: str, message: str,
                                event_date: datetime | None = None) -> str:
    identifier = "NT-" + secrets.token_hex(5).upper()
    database["notifications"].insert_one({"notification_id": identifier, "title": title[:160],
        "message": message[:1500], "event_date": event_date,
        "enabled": True, "created_at": datetime.now(timezone.utc), "source": "admin"})
    return identifier


def sync_due_event_notifications(database: Database, days_ahead: int = 7) -> int:
    """Create one in-app reminder for each published event approaching within a week."""
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    from datetime import timedelta
    end += timedelta(days=days_ahead)
    events = list(database["calendar_events"].find({"event_date": {"$gte": start, "$lte": end}}, {"_id": 0}))
    created = 0
    for event in events:
        stable_id = "EVT-" + hashlib.sha256(event["event_id"].encode()).hexdigest()[:16]
        result = database["notifications"].update_one({"notification_id": stable_id}, {"$setOnInsert": {
            "notification_id": stable_id, "title": f"Upcoming: {event['title']}",
            "message": event.get("description") or f"{event.get('category', 'Campus event')} scheduled from the academic calendar.",
            "event_date": event["event_date"], "enabled": True, "source": "calendar",
            "calendar_event_id": event["event_id"], "created_at": now}}, upsert=True)
        created += int(result.upserted_id is not None)
    return created
