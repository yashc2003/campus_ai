from __future__ import annotations
import streamlit as st
from database.mongodb import get_connection_status
from utils.auth import admin_configuration_status
from utils.config import PROJECT_ROOT, get_settings
from utils.ui import load_theme

load_theme(); st.markdown('<div class="eyebrow">PLATFORM FOUNDATION</div>', unsafe_allow_html=True)
st.title("System status")
st.caption("Configuration and local model availability. Secret values are never shown.")
settings = get_settings(); connected, status = get_connection_status()
left, right = st.columns(2)
with left:
    st.subheader("MongoDB")
    (st.success if connected else st.warning)(status)
    st.write(f"**Database name:** `{settings.database_name}`")
    st.write(f"**URI configured:** {'Yes' if settings.mongodb_uri else 'No'}")
    username_ready, password_ready = admin_configuration_status()
    st.write(f"**Admin username configured:** {'Yes' if username_ready else 'No'}")
    st.write(f"**Admin password meets 12 character minimum:** {'Yes' if password_ready else 'No'}")
with right:
    st.subheader("Local inference")
    production = PROJECT_ROOT / "models" / "production" / "config.json"
    candidate = PROJECT_ROOT / "models" / "bert_classifier" / "config.json"
    baseline = PROJECT_ROOT / "models" / "intent_baseline.joblib"
    st.write(f"**Production BERT:** {'Available' if production.exists() else 'Not deployed'}")
    st.write(f"**BERT candidate:** {'Available' if candidate.exists() else 'Not trained'}")
    st.write(f"**Local baseline:** {'Available' if baseline.exists() else 'Will train from bundled dataset on first query'}")
st.divider()
st.markdown("### Optional components")
st.write("PDF/DOCX parsers, BERT weights and Whisper speech models are optional. The app starts without them and reports missing setup when a feature is used.")
st.markdown("### MongoDB setup")
if connected:
    st.markdown("MongoDB is configured in the project-root `.env` file and responding. Restart Streamlit after changing environment settings.")
else:
    st.markdown("1. Copy `.env.example` to `.env` in the project root.\n2. Set `MONGODB_URI` and `DATABASE_NAME`.\n3. Start MongoDB and restart Streamlit.\n4. Set `ADMIN_USERNAME` and a strong `ADMIN_PASSWORD` (12 or more characters) to enable Admin sign-in.")
st.info("Student pages remain read-only or use session data when MongoDB is offline. Saved queries, documents, tickets, notifications and calendar events need a working database.")
