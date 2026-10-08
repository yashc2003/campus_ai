from __future__ import annotations

import re

import streamlit as st
from pymongo.errors import DuplicateKeyError

from database.mongodb import get_database
from database.users import authenticate_student, create_student
from utils.auth import require_admin, sign_out
from utils.ui import load_theme

load_theme()
st.markdown('<div class="eyebrow">CAMPUS AI ACCOUNT</div>', unsafe_allow_html=True)
st.title("Student and Admin access")
st.caption("Create a student account, sign in, or use the separately configured administrator login.")

role = st.session_state.get("campus_ai_role", "guest")
if role == "student" and st.session_state.get("campus_ai_student"):
    student = st.session_state["campus_ai_student"]
    st.success(f"Signed in as {student['full_name']} ({student['email']}).")
    if st.button("Sign out", type="secondary"):
        sign_out()
        st.rerun()
elif role == "admin":
    st.success("Administrator signed in.")
    if st.button("Sign out", type="secondary"):
        sign_out()
        st.rerun()

student_login, student_register, admin_login = st.tabs(
    ["Student sign in", "Create student account", "Admin sign in"]
)

with student_login:
    st.subheader("Student sign in")
    with st.form("student-login-form"):
        login_email = st.text_input("Student email", key="student-login-email")
        login_password = st.text_input("Password", type="password", key="student-login-password")
        login_submit = st.form_submit_button("Sign in", type="primary")
    if login_submit:
        try:
            student = authenticate_student(get_database(), login_email, login_password)
            if student:
                st.session_state.pop("campus_ai_admin", None)
                st.session_state["campus_ai_student"] = student
                st.session_state["campus_ai_role"] = "student"
                st.rerun()
            st.error("Email or password is incorrect.")
        except Exception as exc:
            st.error(f"Sign in could not reach the account database ({exc.__class__.__name__}).")

with student_register:
    st.subheader("Create a student account")
    st.caption("Student passwords are stored as salted PBKDF2 hashes; the original password is never saved.")
    with st.form("student-register-form"):
        full_name = st.text_input("Full name")
        email = st.text_input("Student email")
        student_number = st.text_input("Student ID (optional)")
        password = st.text_input("Create password (10 characters minimum)", type="password")
        confirm_password = st.text_input("Confirm password", type="password")
        register_submit = st.form_submit_button("Create account", type="primary")
    if register_submit:
        clean_email = email.strip().casefold()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", clean_email):
            st.error("Enter a valid email address.")
        elif password != confirm_password:
            st.error("The passwords do not match.")
        elif len(password) < 10:
            st.error("Choose a password with at least 10 characters.")
        else:
            try:
                student = create_student(get_database(), full_name, clean_email, password, student_number)
                st.session_state.pop("campus_ai_admin", None)
                st.session_state["campus_ai_student"] = student
                st.session_state["campus_ai_role"] = "student"
                st.success("Account created. You are now signed in.")
                st.rerun()
            except DuplicateKeyError:
                st.error("An account already uses that email. Sign in or use another address.")
            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Account creation failed ({exc.__class__.__name__}). Check MongoDB and try again.")

with admin_login:
    st.subheader("Administrator sign in")
    if role == "student":
        st.info("You are already signed in. Your account can access all pages in this exhibition workspace.")
    elif role == "admin":
        st.success("Administrator signed in. All pages are available in this session.")
    else:
        st.caption("Administrator accounts are configured by the project owner in the root `.env` file.")
    if role not in {"student", "admin"} and not require_admin():
        st.caption("Admin credentials are checked against the configured environment; they are never stored in MongoDB.")
