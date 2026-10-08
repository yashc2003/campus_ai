from __future__ import annotations

import streamlit as st
from database.mongodb import get_connection_status
from utils.logger import configure_logging
from utils.ui import load_theme

st.set_page_config(page_title="CAMPUS AI | Academic Support", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")
configure_logging(); load_theme()
st.session_state.setdefault("campus_ai_role", "guest")
if st.session_state.get("campus_ai_role") == "student" and not isinstance(st.session_state.get("campus_ai_student"), dict):
    st.session_state["campus_ai_role"] = "guest"
overview = st.Page("pages/home.py", title="Overview", icon="🏠", default=True)
system_status = st.Page("pages/system_status.py", title="System status", icon="⚙️")
account = st.Page("pages/account.py", title="Account", icon="🔐")
feature_specs = [
    ("Dataset & Intents", "pages/dataset_manager.py", "🗃️", "Phase 2 · Admin", "Clean datasets, configure labeled intents and create reproducible splits."),
    ("AI Assistant", "pages/ai_assistant.py", "🤖", "Phase 5", "Classify student questions and retrieve source-backed answers."),
    ("Knowledge Base", "pages/knowledge_base.py", "📚", "Phase 6", "Index official PDF, DOCX and text sources, then inspect retrieved passages."),
    ("Voice Assistant", "pages/voice_assistant.py", "🎤", "Phase 8", "Transcribe local audio with Whisper and run the student query workflow."),
    ("Academic Calendar", "pages/calendar.py", "📅", "Phase 11", "View and administer campus dates and deadlines."),
    ("Notifications", "pages/notifications.py", "🔔", "Phase 11", "View in-app campus notices and upcoming event reminders."),
    ("Analytics", "pages/analytics.py", "📊", "Phase 12 · Admin", "Live usage, language, intent, confidence and ticket reporting."),
    ("Model Performance", "pages/model_performance.py", "🧠", "Phase 4", "Compare measured held-out metrics and inspect confusion matrices."),
    ("Notice Summarizer", "pages/notice_summarizer.py", "📄", "Phase 10 · Admin", "Extract text, written dates and action statements for staff review."),
    ("Admin", "pages/admin.py", "🛡️", "Phase 9/13/14 · Admin", "Manage tickets, review feedback and export approved corrections."),
    ("Settings", "pages/settings.py", "⚙️", "Phase 14 · Admin", "Inspect runtime settings and model deployment gates."),
]
feature_pages = [st.Page(path, title=title, icon=icon) for title, path, icon, _, _ in feature_specs]
navigation = st.navigation([overview, system_status, account, *feature_pages], position="hidden")
with st.sidebar:
    st.markdown('<div class="sidebar-brand"><span class="brand-icon">C</span><div><b>CAMPUS AI</b><small>ACADEMIC SUPPORT</small></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section">WORKSPACE</div>', unsafe_allow_html=True)
    st.page_link(overview, label="Overview", icon="🏠")
    st.page_link(system_status, label="System status", icon="⚙️")
    st.page_link(account, label="Student / Admin sign in", icon="🔐")
    st.markdown('<div class="sidebar-section">PLATFORM</div>', unsafe_allow_html=True)
    for page, (label, _, icon, phase, _) in zip(feature_pages, feature_specs):
        st.page_link(page, label=label, icon=icon, help=phase)
    st.divider()
    connected, connection_message = get_connection_status()
    current_role = st.session_state.get("campus_ai_role", "guest")
    current_student = st.session_state.get("campus_ai_student", {})
    role_label = "Administrator · Full access" if current_role == "admin" else (
        f"Student · {current_student.get('full_name', '')} · Full access" if current_role == "student" else "Guest"
    )
    st.caption(f"Workspace role · {role_label}")
    st.caption(f"MongoDB · {'🟢 Connected' if connected else '🟠 Offline'}")
    if not connected: st.caption(connection_message)
    st.markdown('<div class="sidebar-footer">SMART QUERIES · BETTER ANSWERS<br>SMARTER CAMPUS</div>', unsafe_allow_html=True)
navigation.run()
