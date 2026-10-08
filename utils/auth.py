from __future__ import annotations

import hmac
import os

import streamlit as st
from dotenv import dotenv_values

from utils.config import PROJECT_ROOT


def _admin_credentials() -> tuple[str, str]:
    """Read current local settings too, so Streamlit sees .env edits without a restart."""
    local = dotenv_values(PROJECT_ROOT / ".env")
    username = os.getenv("ADMIN_USERNAME") or str(local.get("ADMIN_USERNAME") or "")
    password = os.getenv("ADMIN_PASSWORD") or str(local.get("ADMIN_PASSWORD") or "")
    return username.strip(), password


def admin_configuration_status() -> tuple[bool, bool]:
    username, password = _admin_credentials()
    return bool(username), len(password) >= 12


def require_admin() -> bool:
    """Open all exhibition pages after one successful student or administrator sign-in."""
    role = st.session_state.get("campus_ai_role")
    if role == "admin":
        return True
    if role == "student" and isinstance(st.session_state.get("campus_ai_student"), dict):
        return True
    username, password = _admin_credentials()
    if not username or len(password) < 12:
        st.warning("Admin tools are locked. Configure ADMIN_USERNAME and an ADMIN_PASSWORD of at least 12 characters in .env.")
        return False
    st.subheader("Administrator sign in")
    with st.form("admin-auth"):
        entered_user = st.text_input("Username")
        entered_password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Sign in", type="primary")
    if submit:
        # Constant time comparisons avoid leaking which credential matched.
        user_ok = hmac.compare_digest(entered_user, username)
        pass_ok = hmac.compare_digest(entered_password, password)
        if user_ok and pass_ok:
            st.session_state.pop("campus_ai_student", None)
            st.session_state["campus_ai_role"] = "admin"
            st.rerun()
        st.error("Invalid sign-in.")
    return False


def require_signed_in() -> dict | None:
    """Return the active account for student workflows without re-authenticating on each page."""
    if st.session_state.get("campus_ai_role") == "admin":
        return {"student_id": None, "full_name": "Administrator", "email": "Admin account"}
    student = st.session_state.get("campus_ai_student")
    if st.session_state.get("campus_ai_role") == "student" and isinstance(student, dict):
        return student
    st.info("Sign in once to access all CAMPUS AI pages for this session.")
    st.page_link("pages/account.py", label="Open student registration and sign in", icon="🔐")
    return None


def sign_out() -> None:
    st.session_state.pop("campus_ai_role", None)
    st.session_state.pop("campus_ai_student", None)
    st.session_state.pop("campus_ai_admin", None)
