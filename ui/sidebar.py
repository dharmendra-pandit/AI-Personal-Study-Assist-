import hashlib
import re

import streamlit as st

from src.db import vector
from src.services.ingest import ingest_document


def _key(source: str) -> str:
    """Stable widget key per document (survives other files being added or removed)."""
    return "pick_" + hashlib.md5(source.encode("utf-8")).hexdigest()[:10]


def _label(source: str) -> str:
    # checkbox labels are markdown; keep file names literal
    return re.sub(r"([\\`*_\[\]<>#~|])", r"\\\1", source)


def _select(sources: list[str], value: bool):
    for s in sources:
        st.session_state[_key(s)] = value


def _open_history(source: str):
    st.session_state.history_source = source
    st.session_state.page = "History"


def selected_documents() -> list[str] | None:
    """Ticked documents, or None when nothing (or everything) is ticked: use all."""
    sources = vector.list_sources()
    picked = [s for s in sources if st.session_state.get(_key(s))]
    return picked if picked and len(picked) < len(sources) else None


def _uploader():
    # a new key after processing empties the uploader, so files are not processed twice
    upload_round = st.session_state.setdefault("upload_round", 0)
    files = st.file_uploader("Add PDF or DOCX files", type=["pdf", "docx"],
                             accept_multiple_files=True, key=f"uploader_{upload_round}")
    if st.button("Process files", type="primary", disabled=not files, width="stretch"):
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


def _documents(sources: list[str]):
    viewing = st.session_state.get("page") == "History" and st.session_state.get("history_source")
    for s in sources:
        pick, hist = st.columns([7, 1], vertical_alignment="center", gap="small")
        pick.checkbox(_label(s), key=_key(s), help=s)
        hist.button(":material/history:", key="hist_" + _key(s), help=f"History of {s}",
                    type="primary" if s == viewing else "tertiary",
                    on_click=_open_history, args=(s,))

    ticked = sum(bool(st.session_state.get(_key(s))) for s in sources)
    all_btn, none_btn = st.columns(2)
    all_btn.button("Select all", type="tertiary", width="stretch", disabled=ticked == len(sources),
                   on_click=_select, args=(sources, True))
    none_btn.button("Clear", type="tertiary", width="stretch", disabled=not ticked,
                    on_click=_select, args=(sources, False))

    chosen = selected_documents()
    using = f"{len(chosen)} of {len(sources)} documents" if chosen else "all documents"
    st.caption(f"Ask, Notes, Quiz, Progress and Plan use **{using}**. Tick documents to "
               f"narrow it down; none ticked means all. {vector.count()} chunks indexed.")


def render() -> list[str] | None:
    """Library manager. Returns the selected documents, or None for all of them."""
    with st.sidebar:
        st.header("Library")
        _uploader()

        sources = vector.list_sources()
        st.header("Documents")
        if sources:
            _documents(sources)
        else:
            st.caption("No documents yet.")

        if sources:
            st.button("Clear library", width="stretch", on_click=_clear_library, args=(sources,))
    return selected_documents()


def _clear_library(sources: list[str]):
    # a callback, because ticked checkboxes cannot be reset once they are drawn
    vector.reset()
    _select(sources, False)
    st.session_state.update(messages=[], notes=None, quiz=None, quiz_result=None)
