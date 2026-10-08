from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd
from pymongo.database import Database


def load_dashboard_metrics(database: Database) -> dict:
    queries = list(database["queries"].find(
        {}, {"timestamp": 1, "predicted_intent": 1, "confidence": 1, "_id": 0}
    ).sort("timestamp", -1).limit(5000))
    tickets = database["tickets"]
    documents = database["documents"]

    confidence_result = list(database["queries"].aggregate([
        {"$match": {"confidence": {"$type": "number"}}},
        {"$group": {"_id": None, "average": {"$avg": "$confidence"}}},
    ]))
    average_confidence = (float(np.asarray([confidence_result[0]["average"]])[0])
                          if confidence_result else None)

    daily_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    for row in queries:
        timestamp = row.get("timestamp")
        if isinstance(timestamp, datetime):
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            date_key = timestamp.astimezone(timezone.utc).date().isoformat()
        elif isinstance(timestamp, str) and timestamp:
            date_key = timestamp[:10]
        else:
            continue
        daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
        label = str(row.get("predicted_intent") or "Unclassified")
        category_counts[label] = category_counts.get(label, 0) + 1

    daily = pd.DataFrame(sorted(daily_counts.items()), columns=["date", "queries"])
    if not daily.empty:
        daily["date"] = pd.to_datetime(daily["date"])
    categories = pd.DataFrame(sorted(category_counts.items(), key=lambda item: item[1], reverse=True),
                              columns=["intent", "queries"])

    return {
        "total_queries": database["queries"].count_documents({}),
        "open_tickets": tickets.count_documents({"status": {"$in": ["Open", "Assigned", "In Progress"]}}),
        "documents": documents.count_documents({}),
        "average_confidence": average_confidence,
        "daily_queries": daily,
        "intent_counts": categories,
    }
