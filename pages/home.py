from __future__ import annotations
import logging
import plotly.express as px
import streamlit as st
from analytics.metrics import load_dashboard_metrics
from database.mongodb import get_connection_status, get_database
from utils.ui import load_theme

logger = logging.getLogger(__name__)
load_theme()
st.markdown('<div class="eyebrow">CAMPUS INTELLIGENCE PLATFORM <span class="live-dot"></span></div>', unsafe_allow_html=True)
st.markdown('<div class="hero-row"><div><h1>Your campus,<br><span>in the know.</span></h1><p class="hero-subtitle">Ask academic questions, find official source material, and get staff support when you need it.</p></div><div class="hero-orb"><div class="orb-core">✦</div><span class="orb-ring ring-one"></span><span class="orb-ring ring-two"></span><span class="orb-caption">CAMPUS<br>INTELLIGENCE</span></div></div>', unsafe_allow_html=True)
actions = st.columns(3)
for col, title, page, icon in zip(actions, ["Ask Campus AI", "Voice Assistant", "College Knowledge Base"], ["pages/ai_assistant.py", "pages/voice_assistant.py", "pages/knowledge_base.py"], ["🤖", "🎤", "📚"]):
    with col: st.page_link(page, label=title, icon=icon)

connected, message = get_connection_status()
st.markdown('<div class="section-heading"><div><span class="section-kicker">LIVE OVERVIEW</span><h2>Campus at a glance</h2></div></div>', unsafe_allow_html=True)
if not connected:
    st.info(f"Live metrics need MongoDB. {message}. No sample counts or model results are displayed.")
    columns = st.columns(4)
    for column, label in zip(columns, ["TOTAL QUERIES", "OPEN TICKETS", "KNOWLEDGE FILES", "AVG. CONFIDENCE"]):
        with column:
            st.markdown(f'<div class="metric-card"><div class="metric-top"><small>{label}</small></div><div class="metric-value">—</div><div class="metric-caption">Waiting for live database</div></div>', unsafe_allow_html=True)
else:
    try:
        metrics = load_dashboard_metrics(get_database())
        cols = st.columns(4)
        cards = [("TOTAL QUERIES", f"{metrics['total_queries']:,}", "Recorded questions"),
                 ("OPEN TICKETS", f"{metrics['open_tickets']:,}", "Need staff follow-up"),
                 ("KNOWLEDGE FILES", f"{metrics['documents']:,}", "Indexed sources"),
                 ("AVG. CONFIDENCE", f"{metrics['average_confidence']:.1%}" if metrics["average_confidence"] is not None else "—", "Stored predictions")]
        for column, (label, value, caption) in zip(cols, cards):
            with column: st.markdown(f'<div class="metric-card"><div class="metric-top"><small>{label}</small></div><div class="metric-value">{value}</div><div class="metric-caption">{caption}</div></div>', unsafe_allow_html=True)
        left, right = st.columns([1.2, 1])
        with left:
            if metrics["daily_queries"].empty: st.info("Query activity will appear here after the first recorded query.")
            else: st.plotly_chart(px.area(metrics["daily_queries"], x="date", y="queries", title="Questions over time"), use_container_width=True)
        with right:
            if metrics["intent_counts"].empty: st.info("Intent distribution is not available yet.")
            else: st.plotly_chart(px.pie(metrics["intent_counts"], names="intent", values="queries", hole=.6, title="Question categories"), use_container_width=True)
    except Exception as exc:
        logger.exception("Dashboard metrics could not be loaded")
        st.error(f"MongoDB responded, but live metrics failed to load ({exc.__class__.__name__}).")

st.markdown('<div class="section-heading lower-heading"><div><span class="section-kicker">STUDENT SUPPORT</span><h2>One workspace for campus questions</h2></div></div>', unsafe_allow_html=True)
features = st.columns(3)
for col, title, description, icon in zip(features, ["Intent intelligence", "Verified answers", "Human follow-up"], ["See the predicted topic and confidence for each query.", "Answers cite actual passages from indexed campus documents.", "Create a support ticket when information is missing or uncertain."], ["🤖", "📚", "🎫"]):
    with col: st.markdown(f'<div class="feature-card"><div class="feature-top"><span>CAMPUS AI</span><b>{icon}</b></div><h3>{title}</h3><p>{description}</p></div>', unsafe_allow_html=True)
st.markdown('<div class="page-foot"><span>CAMPUS AI · ACADEMIC SUPPORT PLATFORM</span><span>EXHIBITION BUILD · LOCAL FIRST</span></div>', unsafe_allow_html=True)
