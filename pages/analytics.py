from __future__ import annotations
from datetime import datetime, timezone
import pandas as pd
import plotly.express as px
import streamlit as st
from database.mongodb import get_connection_status, get_database
from database.settings import get_runtime_settings
from utils.auth import require_admin
from utils.ui import load_theme

load_theme(); st.markdown('<div class="eyebrow">LIVE STUDENT SUPPORT METRICS</div>', unsafe_allow_html=True)
st.title("Analytics")
st.caption("All figures are queried from MongoDB. Query retention is bounded to the most recent 20,000 records for charts.")
if not require_admin(): st.stop()
connected, message = get_connection_status(); db = None
if connected:
    try: db = get_database()
    except Exception as exc: connected, message = False, exc.__class__.__name__
if db is None: st.warning(f"MongoDB unavailable: {message}"); st.stop()
now = datetime.now(timezone.utc); today = now.date().isoformat()
queries_collection = db["queries"]; ticket_collection = db["tickets"]
records = list(queries_collection.find({}, {"_id": 0, "query": 1, "timestamp": 1, "predicted_intent": 1, "confidence": 1, "language": 1, "status": 1}).sort("timestamp", -1).limit(20000))
total = queries_collection.count_documents({})
today_count = queries_collection.count_documents({"timestamp": {"$gte": datetime(now.year, now.month, now.day, tzinfo=timezone.utc)}})
threshold = get_runtime_settings(db)["medium_confidence_threshold"]
unresolved = queries_collection.count_documents({"$or": [{"status": "unresolved"}, {"confidence": {"$lt": threshold}}]})
ticket_count = ticket_collection.count_documents({})
ticket_open = ticket_collection.count_documents({"status": {"$in": ["Open", "Assigned", "In Progress"]}})
avg_result = list(queries_collection.aggregate([
    {"$match": {"confidence": {"$type": "number"}}},
    {"$group": {"_id": None, "avg": {"$avg": "$confidence"}}},
]))
avg = avg_result[0]["avg"] if avg_result else None
cols = st.columns(6)
for col, label, value in zip(cols, ["Total queries", "Today", "Resolved", "Unresolved / low confidence", "Tickets", "Average confidence"],
    [total, today_count, queries_collection.count_documents({"status": "answered"}), unresolved, ticket_count, f"{avg:.1%}" if avg is not None else "—"]):
    col.metric(label, value)
if not records: st.info("No query events exist yet. Use Ask Campus AI after MongoDB is connected."); st.stop()
frame = pd.DataFrame(records)
frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
left, right = st.columns(2)
with left:
    by_day = frame.dropna(subset=["timestamp"]).assign(day=lambda x: x.timestamp.dt.date).groupby("day").size().reset_index(name="queries")
    if not by_day.empty: st.plotly_chart(px.line(by_day, x="day", y="queries", markers=True, title="Queries over time"), use_container_width=True)
    intents = frame.predicted_intent.fillna("Unknown").value_counts().rename_axis("intent").reset_index(name="queries")
    st.plotly_chart(px.bar(intents, x="queries", y="intent", orientation="h", title="Intent distribution"), use_container_width=True)
    top = frame["query"].fillna("").value_counts().head(10).rename_axis("question").reset_index(name="count")
    if not top.empty: st.dataframe(top, use_container_width=True, hide_index=True)
with right:
    langs = frame.language.fillna("Unknown").value_counts().rename_axis("language").reset_index(name="queries")
    st.plotly_chart(px.pie(langs, names="language", values="queries", title="Language / script mix", hole=.45), use_container_width=True)
    conf = pd.to_numeric(frame.confidence, errors="coerce").dropna()
    if not conf.empty: st.plotly_chart(px.histogram(x=conf, nbins=20, range_x=[0, 1], title="Prediction confidence distribution"), use_container_width=True)
    ticket_rows = list(ticket_collection.find({}, {"_id": 0, "status": 1}))
    if ticket_rows:
        statuses = pd.DataFrame(ticket_rows).status.value_counts().rename_axis("status").reset_index(name="tickets")
        st.plotly_chart(px.bar(statuses, x="status", y="tickets", title="Ticket status"), use_container_width=True)
    unresolved_frame = frame[frame.status.eq("unresolved")] if "status" in frame else frame.iloc[0:0]
    top_unresolved = unresolved_frame["query"].fillna("").value_counts().head(10).rename_axis("unresolved question").reset_index(name="count")
    if not top_unresolved.empty: st.dataframe(top_unresolved, use_container_width=True, hide_index=True)
st.caption(f"Query sample: {len(frame):,} latest records · total stored: {total:,}. Today uses UTC boundaries.")
