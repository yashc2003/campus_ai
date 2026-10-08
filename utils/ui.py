from pathlib import Path

import streamlit as st


def load_theme() -> None:
    css = Path(__file__).resolve().parents[1] / "assets" / "theme.css"
    st.markdown(f"<style>{css.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
