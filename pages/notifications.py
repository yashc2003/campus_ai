from __future__ import annotations

from datetime import date, datetime, time, timezone

import streamlit as st

from database.events import publish_notice_notification, sync_due_event_notifications
from database.mongodb import get_connection_status, get_database
from utils.auth import require_admin
from utils.ui import load_theme

load_theme(); st.markdown('<div class="eyebrow">IN-APP CAMPUS UPDATES</div>', unsafe_allow_html=True)
st.title("Notifications")
st.caption("In-app only. Email and SMS delivery are not configured.")
connected, message = get_connection_status(); db = None
if connected:
    try: db = get_database()
    except Exception as exc: connected, message = False, exc.__class__.__name__
if db is None:
    st.warning(f"MongoDB unavailable: {message}")
else:
    is_admin = require_admin()
    try: created_count = sync_due_event_notifications(db)
    except Exception: created_count = 0
    if created_count: st.info(f"Generated {created_count} reminder(s) from upcoming published calendar events.")
    if is_admin:
        with st.expander("Publish notification"):
            with st.form("notify"):
                title = st.text_input("Title")
                body = st.text_area("Message")
                date_enabled = st.checkbox("Attach an official event date")
                event_date = st.date_input("Date", value=date.today(), disabled=not date_enabled)
                submit = st.form_submit_button("Publish", type="primary")
            if submit:
                if not title.strip() or not body.strip(): st.error("Title and message are required.")
                else:
                    when = datetime.combine(event_date, time.min, tzinfo=timezone.utc) if date_enabled else None
                    identifier = publish_notice_notification(db, title, body, when)
                    st.success(f"Published notification {identifier}."); st.rerun()
    notice_filter = {} if is_admin else {"enabled": True}
    notices = list(db["notifications"].find(notice_filter, {"_id": 0}).sort("created_at", -1).limit(100))
    if not notices: st.info("There are no campus notifications.")
    for notice in notices:
        with st.container(border=True):
            st.markdown(f"**{notice.get('title', 'Campus update')}**")
            st.write(notice.get("message", ""))
            if notice.get("event_date"): st.caption(f"Event date: {notice['event_date']:%d %b %Y}")
            if not notice.get("enabled", True): st.caption("Disabled")
            elif is_admin and st.button("Disable notification", key=f"disable-{notice['notification_id']}"):
                db["notifications"].update_one({"notification_id": notice["notification_id"]}, {"$set": {"enabled": False}})
                st.rerun()
