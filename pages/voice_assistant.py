from __future__ import annotations
import streamlit as st
from database.mongodb import get_connection_status, get_database
from database.queries import record_query
from nlp.inference import predict
from nlp.language_detection import detect_language
from rag.answer_generator import verified_answer
from rag.vector_store import search_documents
from utils.auth import require_signed_in
from voice.speech_to_text import transcribe_audio
from utils.ui import load_theme

load_theme(); st.markdown('<div class="eyebrow">VOICE QUERY · LOCAL WHISPER</div>', unsafe_allow_html=True)
st.title("Voice Assistant")
st.caption("Whisper speech recognition runs on your machine. English, Marathi and Hindi support depends on the chosen Whisper model.")
account = require_signed_in()
if account is None: st.stop()
st.caption(f"Signed in as {account['full_name']} · {account['email']}")
model_name = st.selectbox("Speech model", ["tiny", "base", "small"], index=1,
    format_func=lambda name: {"tiny": "Tiny · fastest", "base": "Base · recommended", "small": "Small · higher accuracy, slower"}[name])
audio = st.audio_input("Record a voice question") if hasattr(st, "audio_input") else None
if audio is None: audio = st.file_uploader("Or upload an audio clip", type=["wav", "mp3", "m4a", "webm"])
language = st.selectbox("Speech language", [("auto", "Auto detect"), ("en", "English"), ("mr", "Marathi"), ("hi", "Hindi")], format_func=lambda item: item[1])[0]
if audio is not None:
    st.audio(audio)
    if st.button("Transcribe and ask", type="primary"):
        try:
            transcript, whisper_language = transcribe_audio(audio.getvalue(), language, model_name)
            if not transcript: st.warning("No speech transcription was returned. Type your question in Ask Campus AI instead.")
            else:
                st.markdown("#### Transcribed query"); st.write(transcript)
                code, label = detect_language(transcript)
                st.caption(f"Detected script: {label} · Whisper code: {whisper_language or 'not reported'}")
                prediction = predict(transcript)
                st.write(f"**Intent:** {prediction['intent']} · **Confidence:** {prediction['confidence']:.1%}")
                connected, message = get_connection_status(); db = None
                if connected:
                    try: db = get_database()
                    except Exception: connected, message = False, "MongoDB unavailable"
                evidence = search_documents(db, transcript) if db else []
                answer = verified_answer(evidence); st.write(answer["answer"])
                for source in answer["sources"]:
                    st.caption(f"Source: {source['filename']} · Page {source.get('page') or 'not available'} · Relevance {source['relevance']:.1%}")
                if db: record_query(db, transcript, prediction, code, evidence, answer["answer"],
                    answer["found"], account["student_id"])
                else: st.info(f"Query not saved because MongoDB is offline: {message}")
        except (RuntimeError, ValueError) as exc: st.error(str(exc))
        except Exception as exc: st.error(f"Voice workflow failed: {exc.__class__.__name__}")
