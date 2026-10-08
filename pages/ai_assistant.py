from __future__ import annotations
from datetime import datetime, timezone
import streamlit as st
from database.datasets import get_intent_categories
from database.mongodb import get_connection_status, get_database
from database.queries import record_feedback, record_query
from database.settings import DEFAULTS, get_runtime_settings
from database.tickets import create_ticket
from nlp.confidence import confidence_band
from nlp.inference import predict
from nlp.language_detection import detect_language
from rag.answer_generator import verified_answer
from rag.vector_store import search_documents
from utils.auth import require_signed_in
from utils.ui import load_theme

load_theme()
st.markdown('<div class="eyebrow">STUDENT WORKSPACE · VERIFIED ACADEMIC HELP</div>', unsafe_allow_html=True)
st.title("Ask Campus AI")
st.caption("Intent predictions come from a local model. Answers appear only when they match indexed official document passages.")
account = require_signed_in()
if account is None: st.stop()
st.caption(f"Signed in as {account['full_name']} · {account['email']}")
connected, message = get_connection_status(); database = None
if connected:
    try: database = get_database()
    except Exception as exc: connected, message = False, f"Database unavailable: {exc.__class__.__name__}"
if not connected: st.warning(f"MongoDB is offline: {message}. Intent prediction works locally; saved queries, citations and tickets need MongoDB.")

with st.form("campus-ai-ask", clear_on_submit=False):
    query = st.text_area("Your academic question", placeholder="When is the exam form deadline?", height=105)
    submitted = st.form_submit_button("Ask Campus AI", type="primary")

if submitted:
    if not query.strip():
        st.warning("Enter a question first.")
    else:
        try:
            question = query.strip()
            prediction = predict(question)
            language_code, language_name = detect_language(question)
            thresholds = get_runtime_settings(database) if database is not None else DEFAULTS
            evidence = search_documents(database, question) if database is not None else []
            answer = verified_answer(evidence)
            query_id = record_query(database, question, prediction, language_code, evidence,
                answer["answer"], answer["found"], account["student_id"]) if database is not None else None
            st.session_state["last_campus_result"] = {
                "query": question, "student_name": account["full_name"],
                "student_id": account["student_id"], "prediction": prediction,
                "language": language_code, "language_name": language_name,
                "thresholds": thresholds, "evidence": evidence, "answer": answer,
                "query_id": query_id, "ticket_id": None,
            }
        except (ValueError, RuntimeError) as exc: st.error(str(exc))
        except Exception as exc: st.error(f"The request could not be completed ({exc.__class__.__name__}). Check MongoDB and the local model setup.")

result = st.session_state.get("last_campus_result")
if result:
    prediction = result["prediction"]; score = float(prediction["confidence"])
    thresholds = result["thresholds"]
    band = confidence_band(score, thresholds["high_confidence_threshold"], thresholds["medium_confidence_threshold"])
    st.markdown(f"**Intent:** {prediction['intent']} · **Confidence:** {score:.1%} · **{band}**")
    st.caption(f"Detected language: {result['language_name']} · Classifier: {prediction['backend']}")
    if score < thresholds["medium_confidence_threshold"]:
        st.warning("I am not completely confident about this question. Rephrase it, choose a category, or ask a staff member.")
    answer = result["answer"]
    if answer["found"]:
        st.success("Verified document passage found")
        st.write(answer["answer"])
        for source in answer["sources"]:
            page = f" · Page {source['page']}" if source.get("page") else ""
            st.caption(f"Source: {source.get('filename', 'Indexed document')}{page} · Relevance {source['relevance']:.1%}")
    else:
        st.info(answer["answer"])
        st.caption("No citation is shown because no sufficiently relevant document passage was retrieved.")
    if result["query_id"]:
        left, right = st.columns(2)
        if left.button("Helpful", key=f"helpful-{result['query_id']}"):
            record_feedback(database, result["query_id"], True); st.success("Feedback recorded.")
        if right.button("Not helpful", key=f"not-helpful-{result['query_id']}"):
            record_feedback(database, result["query_id"], False); st.success("Feedback recorded for staff review.")
        with st.expander("Suggest a corrected intent"):
            options = [item["name"] for item in get_intent_categories(database) if item.get("active", True)]
            with st.form(f"correct-intent-{result['query_id']}"):
                corrected = st.selectbox("Correct category", options)
                submit_correction = st.form_submit_button("Send correction for staff review")
            if submit_correction:
                record_feedback(database, result["query_id"], False, corrected)
                st.success("Correction sent to staff review. It will not retrain the model automatically.")
    if database is not None and (score < thresholds["medium_confidence_threshold"] or not answer["found"]):
        with st.expander("Create a staff support ticket"):
            st.write("Ticket priority and assigned department are set from the query and selected intent.")
            category_options = [item["name"] for item in get_intent_categories(database) if item.get("active", True)]
            selected_intent = st.selectbox("Choose the department / topic", category_options,
                index=category_options.index(prediction["intent"]) if prediction["intent"] in category_options else 0,
                key=f"ticket-intent-{result['query_id']}")
            if result.get("ticket_id"):
                st.success(f"Ticket {result['ticket_id']} created. Keep the ID to check status.")
            elif st.button("Create ticket", type="primary", key=f"create-ticket-{result['query_id']}"):
                ticket_id = create_ticket(database, result["query"], selected_intent, score,
                    result["student_name"], result["student_id"])
                result["ticket_id"] = ticket_id
                st.session_state["last_campus_result"] = result
                st.success(f"Ticket {ticket_id} created. Keep the ID to check status.")

st.divider()
st.markdown("#### What the assistant can verify")
st.write("Only indexed college documents can support an answer. Without a relevant passage, Campus AI says it could not find a verified answer and offers staff follow-up.")
if database is not None:
    with st.expander("Check a support ticket"):
        ticket_code = st.text_input("Ticket ID")
        if st.button("Look up ticket", key="ticket-lookup") and ticket_code.strip():
            ticket = database["tickets"].find_one({"ticket_id": ticket_code.strip().upper()}, {"_id": 0, "ticket_id": 1, "status": 1, "priority": 1, "resolution": 1})
            if ticket:
                st.write(f"**{ticket['ticket_id']}** · {ticket['status']} · {ticket['priority']} priority")
                if ticket.get("resolution"): st.write(ticket["resolution"])
            else: st.info("No ticket matches that ID.")
