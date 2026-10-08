from __future__ import annotations

import json
import secrets
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pymongo.database import Database

from utils.config import PROJECT_ROOT

CATEGORY_FILE = PROJECT_ROOT / "data" / "intent_categories.json"


def load_category_defaults() -> list[dict]:
    return json.loads(CATEGORY_FILE.read_text(encoding="utf-8"))


def get_intent_categories(database: Database) -> list[dict]:
    collection = database["intents"]
    if collection.count_documents({}) == 0:
        now = datetime.now(timezone.utc)
        collection.insert_many([{**item, "active": True, "created_at": now}
                                for item in load_category_defaults()])
    return list(collection.find({}, {"_id": 0}).sort("name", 1))


def add_intent_category(database: Database, name: str, description: str) -> None:
    name = name.strip()
    if not name:
        raise ValueError("Enter an intent name.")
    existing = database["intents"].find_one({"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}})
    if existing:
        raise ValueError("That intent category already exists.")
    database["intents"].insert_one({
        "name": name, "description": description.strip(), "active": True,
        "created_at": datetime.now(timezone.utc),
    })


def update_intent_category(database: Database, name: str, description: str, active: bool) -> None:
    if not active and database["intents"].count_documents({"active": True, "name": {"$ne": name}}) == 0:
        raise ValueError("Keep at least one active intent category.")
    result = database["intents"].update_one(
        {"name": name}, {"$set": {"description": description.strip(), "active": active}})
    if not result.matched_count:
        raise ValueError("Category no longer exists. Refresh the list and try again.")


def save_dataset_import(database: Database, filename: str, cleaned: pd.DataFrame,
                        cleaning_report: dict, split_info: dict) -> str:
    if cleaned.empty:
        raise ValueError("The clean dataset has no usable rows.")
    batch_id = secrets.token_hex(8)
    created_at = datetime.now(timezone.utc)
    records = cleaned.to_dict(orient="records")
    for index, row in enumerate(records):
        row.update({"dataset_id": batch_id, "row_number": index + 1, "created_at": created_at})
    database["dataset_imports"].insert_one({
        "dataset_id": batch_id, "filename": filename, "created_at": created_at,
        "rows_before_cleaning": cleaning_report["rows_before_cleaning"],
        "rows_after_cleaning": len(cleaned), "classes": cleaning_report["classes"],
        "cleaning_report": cleaning_report, "split": split_info,
    })
    database["training_examples"].insert_many(records, ordered=True)
    database["training_examples"].create_index([("dataset_id", 1), ("split", 1)])
    database["training_examples"].create_index([("dataset_id", 1), ("intent", 1)])
    return batch_id


def list_dataset_imports(database: Database, limit: int = 20) -> list[dict]:
    return list(database["dataset_imports"].find({}, {"_id": 0}).sort("created_at", -1).limit(limit))


def import_training_frame(database: Database, dataset_id: str) -> pd.DataFrame:
    rows = list(database["training_examples"].find({"dataset_id": dataset_id}, {"_id": 0}))
    return pd.DataFrame(rows)
