from __future__ import annotations

from datetime import date, datetime, time, timezone

import pandas as pd
import streamlit as st

from database.mongodb import get_connection_status, get_database
from database.events import upsert_event
from utils.auth import require_admin
from utils.ui import load_theme

load_theme(); st.markdown('<div class="eyebrow">CAMPUS SCHEDULE</div>', unsafe_allow_html=True)
st.title("Academic Calendar")
st.caption("Dates are maintained by campus administrators. No deadlines are generated from guesses.")
connected, message = get_connection_status(); db = None
if connected:
    try: db = get_database()
    except Exception as exc: connected, message = False, exc.__class__.__name__
if db is None:
    st.warning(f"MongoDB unavailable: {message}")
else:
    is_admin = require_admin()
    if is_admin:
        with st.expander("Add a campus event", expanded=False):
            with st.form("event-add"):
                title = st.text_input("Event or deadline")
                category = st.selectbox("Category", ["Examination", "Fees", "Assignment", "Placement", "College event", "Notice"])
                event_date = st.date_input("Date", value=date.today())
                description = st.text_area("Details")
                save = st.form_submit_button("Save event", type="primary")
            if save:
                try:
                    event_id = upsert_event(db, title, datetime.combine(event_date, time.min, tzinfo=timezone.utc), category, description)
                    st.success(f"Saved event {event_id}."); st.rerun()
                except ValueError as exc: st.error(str(exc))
    items = list(db["calendar_events"].find({}, {"_id": 0}).sort("event_date", 1).limit(500))
    if not items:
        st.info("No campus dates are published yet.")
    else:
        frame = pd.DataFrame(items)
        frame["event_date"] = pd.to_datetime(frame["event_date"], errors="coerce", utc=True)
        frame["date"] = frame["event_date"].dt.strftime("%d %b %Y")
        st.dataframe(frame[[c for c in ["date", "category", "title", "description"] if c in frame]], use_container_width=True, hide_index=True)
        st.markdown("#### Calendar view")
        frame["month"] = frame["event_date"].dt.strftime("%B %Y")
        month = st.selectbox("Month", frame["month"].dropna().unique().tolist())
        for _, event in frame[frame.month == month].iterrows():
            st.markdown(f"**{event.date} · {event.category}** — {event.title}")
            if event.get("description"): st.caption(event.description)
        if is_admin:
            st.markdown("#### Edit or remove a calendar event")
            chosen_id = st.selectbox("Event", [item["event_id"] for item in items],
                format_func=lambda value: next((f"{item['title']} · {item['event_date']:%d %b %Y}" for item in items if item["event_id"] == value), value))
            chosen = next(item for item in items if item["event_id"] == chosen_id)
            with st.form("event-edit"):
                edit_title = st.text_input("Title", value=chosen["title"])
                edit_category = st.selectbox("Category", ["Examination", "Fees", "Assignment", "Placement", "College event", "Notice"], index=["Examination", "Fees", "Assignment", "Placement", "College event", "Notice"].index(chosen["category"]) if chosen.get("category") in ["Examination", "Fees", "Assignment", "Placement", "College event", "Notice"] else 0)
                raw_date = chosen["event_date"]
                initial_date = pd.to_datetime(raw_date).date()
                edit_date = st.date_input("Date", value=initial_date)
                edit_description = st.text_area("Details", value=chosen.get("description") or "")
                update = st.form_submit_button("Update event")
            if update:
                upsert_event(db, edit_title, datetime.combine(edit_date, time.min, tzinfo=timezone.utc), edit_category, edit_description, chosen_id)
                st.success("Event updated."); st.rerun()
            if st.button("Delete selected event", type="secondary"):
                db["calendar_events"].delete_one({"event_id": chosen_id})
                db["notifications"].update_many({"calendar_event_id": chosen_id}, {"$set": {"enabled": False}})
                st.success("Event removed and its automatic reminder disabled."); st.rerun()
