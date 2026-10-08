from __future__ import annotations
from datetime import datetime, timezone
import pandas as pd
import streamlit as st
from database.datasets import get_intent_categories
from database.mongodb import get_connection_status, get_database
from database.settings import get_runtime_settings
from database.tickets import update_ticket
from utils.auth import require_admin, sign_out
from utils.ui import load_theme

load_theme(); st.markdown('<div class="eyebrow">RESTRICTED STAFF WORKSPACE</div>', unsafe_allow_html=True)
st.title("Admin Dashboard")
if not require_admin(): st.stop()
if st.button("Sign out", key="admin-sign-out"): sign_out(); st.rerun()
connected, message = get_connection_status(); db = None
if connected:
    try: db = get_database()
    except Exception as exc: connected, message = False, exc.__class__.__name__
if db is None: st.error(f"MongoDB is required for administration: {message}"); st.stop()

st.markdown("### Support tickets")
tickets = list(db["tickets"].find({}, {"_id": 0}).sort("created_at", -1).limit(200))
if not tickets: st.info("No support tickets are recorded.")
for ticket in tickets:
    with st.expander(f"{ticket['ticket_id']} · {ticket.get('priority')} priority · {ticket.get('status')}"):
        st.write(ticket.get("query", ""))
        st.caption(f"Intent: {ticket.get('predicted_intent') or 'Unknown'} · Confidence: {ticket.get('confidence') if ticket.get('confidence') is not None else 'unknown'} · Department: {ticket.get('department')}")
        with st.form(f"ticket-{ticket['ticket_id']}"):
            choices = ["Open", "Assigned", "In Progress", "Resolved", "Closed"]
            old_status = ticket.get("status", "Open")
            status = st.selectbox("Status", choices, index=choices.index(old_status) if old_status in choices else 0)
            assigned_staff = st.text_input("Assigned staff", value=ticket.get("assigned_staff") or "")
            resolution = st.text_area("Staff resolution", value=ticket.get("resolution") or "")
            save = st.form_submit_button("Update ticket")
        if save: update_ticket(db, ticket["ticket_id"], status, resolution, assigned_staff); st.success("Ticket updated."); st.rerun()

st.markdown("### Feedback and intent corrections")
feedback = list(db["feedback"].find({"review_status": {"$in": ["pending", "new"]}}, {"_id": 0}).sort("created_at", -1).limit(300))
if not feedback: st.info("No feedback is awaiting review.")
categories = get_intent_categories(db)
active_intents = [item["name"] for item in categories if item.get("active", True)]
for item in feedback:
    query_record = db["queries"].find_one({"query_id": item["query_id"]}, {"_id": 0}) or {}
    with st.expander(f"{item['query_id']} · {'Helpful' if item.get('helpful') else 'Needs review'}"):
        st.write(query_record.get("query", "Query unavailable"))
        st.caption(f"Predicted intent: {query_record.get('predicted_intent') or 'Unknown'} · confidence: {query_record.get('confidence')}")
        with st.form(f"review-{item['query_id']}"):
            corrected = st.selectbox("Verified intent", active_intents, key=f"label-{item['query_id']}")
            approve = st.form_submit_button("Approve correction for training export")
        if approve:
            db["feedback"].update_one({"query_id": item["query_id"]}, {"$set": {"corrected_intent": corrected, "review_status": "approved", "reviewed_at": datetime.now(timezone.utc)}})
            st.success("Correction approved for controlled training export."); st.rerun()

st.markdown("### Low-confidence queries requiring review")
threshold = get_runtime_settings(db)["medium_confidence_threshold"]
reviewed_ids = {item.get("query_id") for item in db["feedback"].find({}, {"_id": 0, "query_id": 1})}
low_confidence = list(db["queries"].find({"$or": [{"confidence": {"$lt": threshold}}, {"status": "unresolved"}]},
    {"_id": 0, "query_id": 1, "query": 1, "predicted_intent": 1, "confidence": 1, "timestamp": 1}).sort("timestamp", -1).limit(100))
low_confidence = [item for item in low_confidence if item.get("query_id") not in reviewed_ids]
if not low_confidence: st.info("No unreviewed low-confidence or source-unanswered questions are queued.")
for item in low_confidence:
    with st.expander(f"{item.get('predicted_intent') or 'Unknown'} · confidence {item.get('confidence') if item.get('confidence') is not None else 'unknown'}"):
        st.write(item.get("query", ""))
        with st.form(f"low-review-{item['query_id']}"):
            corrected = st.selectbox("Staff-verified intent", active_intents, key=f"low-intent-{item['query_id']}")
            approve = st.form_submit_button("Approve this correction for training export")
        if approve:
            db["feedback"].insert_one({"query_id": item["query_id"], "helpful": False,
                "corrected_intent": corrected, "review_status": "approved",
                "reviewed_at": datetime.now(timezone.utc), "created_at": datetime.now(timezone.utc)})
            st.success("Correction approved for controlled export."); st.rerun()

approved = list(db["feedback"].find({"review_status": "approved", "corrected_intent": {"$ne": None}}, {"_id": 0}))
st.markdown("### Controlled learning")
st.write(f"Approved corrections available for export: **{len(approved)}**. Live queries never trigger automatic retraining.")
records = []
for item in approved:
    query_record = db["queries"].find_one({"query_id": item["query_id"]}, {"_id": 0})
    if query_record and query_record.get("query"):
        records.append({"query": query_record["query"], "intent": item["corrected_intent"], "language": query_record.get("language", ""), "course": "", "semester": "", "timestamp": str(item.get("reviewed_at", "")), "source": "Staff-approved correction"})
if records:
    st.download_button("Prepare training CSV", pd.DataFrame(records).to_csv(index=False).encode("utf-8"), file_name="staff_approved_training_corrections.csv", mime="text/csv")
st.caption("Train a candidate, evaluate it on held-out data, then deploy only if it clears the configured quality gate.")
st.code("python -m training.merge_training_data --corrections data/processed/staff_approved_training_corrections.csv\npython -m training.train_bert --dataset data/processed/approved_training.csv\npython -m training.evaluate --model bert\npython -m training.deploy_model --model bert", language="powershell")
