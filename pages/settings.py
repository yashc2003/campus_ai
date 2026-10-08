from __future__ import annotations
import os
import streamlit as st
from database.mongodb import get_connection_status, get_database
from database.settings import get_runtime_settings, save_runtime_settings
from utils.auth import admin_configuration_status, require_admin
from utils.ui import load_theme

load_theme(); st.markdown('<div class="eyebrow">ADMINISTRATIVE CONFIGURATION</div>', unsafe_allow_html=True)
st.title("Settings")
if not require_admin(): st.stop()
connected, message = get_connection_status(); db = None
if connected:
    try: db = get_database()
    except Exception as exc: connected, message = False, exc.__class__.__name__
if db is None: st.warning(f"MongoDB settings unavailable: {message}"); st.stop()
current = get_runtime_settings(db)
st.markdown("### Assistant fallback thresholds")
st.caption("These values control confidence labels and when a ticket suggestion is shown. Classifier probabilities are not accuracy guarantees.")
with st.form("confidence-settings"):
    high = st.slider("High confidence threshold", .50, 1.0, float(current["high_confidence_threshold"]), .01)
    medium = st.slider("Medium confidence threshold", .10, .95, float(current["medium_confidence_threshold"]), .01)
    save = st.form_submit_button("Save thresholds", type="primary")
if save:
    try:
        save_runtime_settings(db, high, medium)
        st.success("Confidence thresholds saved."); st.rerun()
    except ValueError as exc: st.error(str(exc))
st.markdown("### Deployment gate")
st.write(f"Minimum weighted F1: **{os.getenv('MIN_DEPLOY_F1', '.70')}**")
st.caption("Set MIN_DEPLOY_F1 in .env. A candidate must have an evaluation report and pass this gate before BERT is copied to production.")
st.markdown("### Runtime configuration")
username_ready, password_ready = admin_configuration_status()
st.write(f"**Admin username configured:** {'Yes' if username_ready else 'No'}")
st.write(f"**Admin password meets 12 character minimum:** {'Yes' if password_ready else 'No'}")
st.write("**Database credentials:** hidden")
st.info("Configure secrets in the local .env file. This page never displays MongoDB credentials or passwords.")
