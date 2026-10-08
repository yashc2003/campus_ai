from __future__ import annotations

from functools import lru_cache

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

from utils.config import get_settings


@lru_cache(maxsize=1)
def _client(uri: str) -> MongoClient:
    return MongoClient(uri, serverSelectionTimeoutMS=2200, connectTimeoutMS=2200,
                       appname="CampusAI-Phase1")


def get_database() -> Database:
    settings = get_settings()
    if not settings.mongodb_uri:
        raise RuntimeError("MONGODB_URI is not configured. Copy .env.example to .env and set your MongoDB URI.")
    client = _client(settings.mongodb_uri)
    client.admin.command("ping")
    database = client[settings.database_name]
    ensure_indexes(database)
    return database


def ensure_indexes(database: Database) -> None:
    """Create the few Phase 1 indexes; safe to call on each app rerun."""
    database["queries"].create_index("timestamp")
    database["queries"].create_index("predicted_intent")
    database["tickets"].create_index([("status", 1), ("created_at", -1)])
    database["documents"].create_index("uploaded_at")
    database["intents"].create_index("name", unique=True)
    database["dataset_imports"].create_index("created_at")
    database["queries"].create_index("query_id", unique=True, sparse=True)
    database["feedback"].create_index([("review_status", 1), ("created_at", -1)])
    database["tickets"].create_index("ticket_id", unique=True, sparse=True)
    database["document_chunks"].create_index([("document_id", 1), ("chunk_index", 1)])
    database["documents"].create_index("sha256", unique=True, sparse=True)
    database["calendar_events"].create_index([("event_date", 1), ("category", 1)])
    database["notifications"].create_index("notification_id", unique=True, sparse=True)
    database["notifications"].create_index("enabled")
    database["embeddings_metadata"].create_index("document_id", unique=True, sparse=True)
    database["students"].create_index("email", unique=True)


def get_connection_status() -> tuple[bool, str]:
    settings = get_settings()
    if not settings.mongodb_uri:
        return False, "MONGODB_URI is missing from .env"
    try:
        _client(settings.mongodb_uri).admin.command("ping")
        return True, f"Connected to {settings.database_name}"
    except ServerSelectionTimeoutError:
        return False, "MongoDB is unreachable. Start MongoDB or verify MONGODB_URI."
    except PyMongoError as exc:
        return False, f"MongoDB connection error: {exc.__class__.__name__}"
    except (ValueError, TypeError) as exc:
        return False, f"MongoDB configuration error: {exc.__class__.__name__}"
