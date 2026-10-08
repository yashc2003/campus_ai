from __future__ import annotations

import streamlit as st


def render_phase_page(title: str, phase: str, description: str) -> None:
    st.markdown('<div class="eyebrow">CAMPUS AI · PRODUCT ROADMAP</div>', unsafe_allow_html=True)
    st.title(title)
    st.caption(description)
    st.info(f"**{phase} · Planned** — this module has a working navigation page, but its feature implementation has not started.")
    st.markdown("### Phase 1 foundation is ready")
    st.write("The Streamlit shell, theme, MongoDB configuration, navigation and live dashboard are in place. This page records the next module’s scope without showing sample results as if it were live.")
    st.markdown("### What this phase will add")
    st.write(description)
    st.markdown("### Current status")
    st.progress(0, text="Implementation has not started")
    st.caption("The project brief asks us to complete and verify each phase before moving to the next one.")
