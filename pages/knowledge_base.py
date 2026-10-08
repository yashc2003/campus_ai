from __future__ import annotations

import streamlit as st

from database.mongodb import get_connection_status, get_database
from rag.document_loader import extract_pages
from rag.vector_store import search_documents, store_document
from utils.auth import require_admin
from utils.ui import load_theme

load_theme()
st.markdown('<div class="eyebrow">PHASE 6 · COLLEGE DOCUMENT INTELLIGENCE</div>', unsafe_allow_html=True)
st.title("College Knowledge Base")
st.caption("Search extracted text from official sources. Scanned PDFs require OCR and are not indexed as if searchable.")
connected, message = get_connection_status(); db = None
if connected:
    try: db = get_database()
    except Exception as exc: connected, message = False, exc.__class__.__name__
if db is None:
    st.warning(f"MongoDB is required to store and search indexed documents: {message}")
else:
    with st.expander("Add an official document"):
        if require_admin():
            uploaded = st.file_uploader("PDF, DOCX, or TXT · up to 12 MB", type=["pdf", "docx", "txt"])
            source_type = st.selectbox("Document type", ["Academic notice", "Examination", "Fees", "Syllabus", "Admissions", "Placement", "Calendar", "Other"])
            if uploaded and st.button("Extract and index document", type="primary"):
                try:
                    pages = extract_pages(uploaded.name, uploaded.getvalue())
                    document_id = store_document(db, uploaded.name, uploaded.getvalue(), pages)
                    db["documents"].update_one({"document_id": document_id}, {"$set": {"category": source_type, "uploaded_by": "admin"}})
                    st.success(f"Indexed {uploaded.name}: {sum(bool(p['text'].strip()) for p in pages)} text pages. ID: {document_id}")
                    st.rerun()
                except (ValueError, RuntimeError) as exc: st.error(str(exc))
                except Exception as exc: st.error(f"Indexing failed: {exc.__class__.__name__}")
        else:
            st.info("Admin sign-in is required to upload sources.")
    sources = list(db["documents"].find({}, {"_id": 0}).sort("uploaded_at", -1).limit(200))
    st.markdown("#### Indexed official sources")
    if sources:
        st.dataframe([{key: item.get(key) for key in ("filename", "category", "page_count", "chunk_count", "active", "uploaded_at")} for item in sources], use_container_width=True, hide_index=True)
        if require_admin():
            selected_doc = st.selectbox("Manage source", [item["document_id"] for item in sources],
                format_func=lambda value: next((item["filename"] for item in sources if item["document_id"] == value), value))
            selected_record = next(item for item in sources if item["document_id"] == selected_doc)
            with st.form("source-state"):
                active = st.checkbox("Available in student retrieval", value=selected_record.get("active", True))
                save_state = st.form_submit_button("Save source status")
            if save_state:
                db["documents"].update_one({"document_id": selected_doc}, {"$set": {"active": active}})
                st.success("Source status updated."); st.rerun()
    else: st.info("No official documents have been indexed yet.")
    st.markdown("#### Search the indexed passages")
    question = st.text_input("Search question", placeholder="MCA exam form deadline")
    if question:
        results = search_documents(db, question)
        if not results: st.info("No relevant indexed passage found.")
        for result in results:
            page = f" · Page {result['page']}" if result.get("page") else ""
            with st.container(border=True):
                st.markdown(f"**{result['filename']}**{page} · relevance {result['relevance']:.1%}")
                st.write(result["text"])
