import streamlit as st

from src.db import vector
from src.services.ingest import ingest_document


def _open_history(source: str):
    st.session_state.history_source = source
    st.session_state.page = "History"


def render() -> str | None:
    """Document manager. Returns the selected source filename, or None for all documents."""
    with st.sidebar:
        st.header("Library")
        # a new key after processing empties the uploader, so files are not processed twice
        upload_round = st.session_state.setdefault("upload_round", 0)
        files = st.file_uploader("Add PDF or DOCX files", type=["pdf", "docx"],
                                 accept_multiple_files=True, key=f"uploader_{upload_round}")
        if st.button("Process files", type="primary", disabled=not files,
                     width="stretch"):
            known, outcome = vector.list_sources(), []
            for f in files:
                with st.spinner(f"Processing {f.name}..."):
                    try:
                        n = ingest_document(f.name, f.getvalue())
                        again = " (replaced the earlier copy)" if f.name in known else ""
                        outcome.append(("success", f"{f.name}: {n} chunks{again}"))
                    except Exception as e:
                        outcome.append(("error", f"{f.name}: {e}"))
            st.session_state.upload_outcome = outcome
            st.session_state.upload_round += 1
            st.rerun()
        for kind, text in st.session_state.pop("upload_outcome", []):
            getattr(st, kind)(text)

        sources = vector.list_sources()
        st.header("Documents")
        if sources:
            viewing = (st.session_state.get("page") == "History"
                       and st.session_state.get("history_source"))
            for i, s in enumerate(sources):
                st.button(s, key=f"doc_{i}", help=f"{s}: view its history",
                          type="primary" if s == viewing else "secondary",
                          on_click=_open_history, args=(s,), width="stretch")
            st.caption(f"{len(sources)} document(s), {vector.count()} chunks indexed. "
                       "Click a document to see its questions, notes and quizzes.")
        else:
            st.caption("No documents yet.")

        st.header("Scope")
        scope = st.selectbox("Notes and quiz use", ["All documents"] + sources,
                             label_visibility="collapsed")

        if sources and st.button("Clear library", width="stretch"):
            vector.reset()
            st.session_state.update(messages=[], notes=None, quiz=None, quiz_result=None)
            st.rerun()
    return None if scope == "All documents" else scope
