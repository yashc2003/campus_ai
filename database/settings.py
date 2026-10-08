from __future__ import annotations
from pymongo.database import Database

DEFAULTS = {"high_confidence_threshold": .85, "medium_confidence_threshold": .60}

def get_runtime_settings(database: Database) -> dict:
    record = database["application_settings"].find_one({"_id": "runtime"}) or {}
    return {**DEFAULTS, **{key: record[key] for key in DEFAULTS if key in record}}

def save_runtime_settings(database: Database, high: float, medium: float) -> None:
    if not (0 < medium < high <= 1):
        raise ValueError("Thresholds must satisfy 0 < medium < high ≤ 1.")
    database["application_settings"].update_one({"_id": "runtime"}, {"$set": {
        "high_confidence_threshold": high, "medium_confidence_threshold": medium}}, upsert=True)
