from __future__ import annotations
from datetime import date, datetime, time, timezone
import streamlit as st
from database.events import publish_notice_notification, upsert_event
from database.mongodb import get_connection_status, get_database
from nlp.notice_extractor import extract_notice_facts
from rag.document_loader import extract_pages
from rag.vector_store import store_document
from utils.auth import require_admin
from utils.ui import load_theme

load_theme(); st.markdown('<div class="eyebrow">OFFICIAL NOTICE REVIEW</div>', unsafe_allow_html=True)
st.title("Notice Summarizer")
st.caption("Extracts text, written dates and action statements for staff review. This review aid does not generate or fill in missing facts.")
if not require_admin(): st.stop()
uploaded = st.file_uploader("Upload notice (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])
connected, message = get_connection_status(); db = None
if connected:
    try: db = get_database()
    except Exception as exc: connected, message = False, exc.__class__.__name__
if uploaded:
    try:
        original = uploaded.getvalue()
        pages = extract_pages(uploaded.name, original)
        content = "\n".join(page["text"] for page in pages if page["text"])
        facts = extract_notice_facts(content)
        st.markdown("#### Review extracted information")
        st.write("**Title candidate:**", facts["title"])
        st.write("**Extractive summary:**", facts["summary"] or "No text extracted")
        st.write("**Dates with source context:**")
        if facts["important_dates"]: st.dataframe(facts["important_dates"], use_container_width=True, hide_index=True)
        else: st.info("No recognizable written dates were found.")
        for label in ("actions", "eligibility", "required_documents"):
            st.markdown(f"**{label.replace('_', ' ').title()}**")
            if facts[label]:
                for item in facts[label]: st.write("• " + item)
            else: st.caption("No matching statement found in the extracted text.")
        if db is None: st.warning(f"MongoDB is needed to save this notice or publish dates: {message}")
        elif st.button("Index this source in the College Knowledge Base"):
            try:
                identifier = store_document(db, uploaded.name, original, pages)
                db["documents"].update_one({"document_id": identifier}, {"$set": {"category": "Academic notice", "uploaded_by": "admin"}})
                st.success(f"Source indexed with extracted passages. Document ID: {identifier}")
            except (ValueError, RuntimeError) as exc: st.error(str(exc))
        if db is not None and facts["important_dates"]:
            date_options = [item["date_text"] + " · " + item["context"] for item in facts["important_dates"]]
            selected = st.selectbox("Select the date that staff reviewed", date_options)
            chosen = facts["important_dates"][date_options.index(selected)]
            category = st.selectbox("Calendar category", ["Examination", "Fees", "Assignment", "Placement", "College event", "Notice"])
            title = st.text_input("Published event title", value=facts["title"])
            confirmed_date = st.date_input("Confirm the calendar date from the source", value=date.today())
            verified = st.checkbox("I checked this date and event against the uploaded official notice")
            if st.button("Publish verified calendar event and reminder", type="primary", disabled=not verified):
                event_date = datetime.combine(confirmed_date, time.min, tzinfo=timezone.utc)
                event_id = upsert_event(db, title, event_date, category, f"{chosen['context']}\nSource: {uploaded.name}")
                notification_id = publish_notice_notification(db, title, f"{chosen['context']}\nSource: {uploaded.name}", event_date)
                st.success(f"Calendar event {event_id} and in-app notice {notification_id} published.")
    except (RuntimeError, ValueError) as exc: st.error(str(exc))
    except Exception as exc: st.error(f"Could not process notice: {exc.__class__.__name__}")
