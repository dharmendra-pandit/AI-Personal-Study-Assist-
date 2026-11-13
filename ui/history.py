from datetime import datetime
from html import escape

import streamlit as st

from src.db import tracking, vector
from ui import theme
from ui.common import show_sources


def _when(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).astimezone().strftime("%d %b %Y, %H:%M")
    except ValueError:
        return iso


def _short(text: str, n: int = 80) -> str:
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _ask_item(item: dict):
    st.markdown(f"**{item['title']}**")
    st.markdown(item["answer"])
    if item.get("sources"):
        show_sources(item["sources"])


def _notes_item(item: dict):
    st.markdown(item["notes"])
    st.download_button("Download as Markdown", item["notes"], file_name="notes.md",
                       mime="text/markdown", key=f"dl_notes_{item['id']}")


def _quiz_item(item: dict):
    for i, q in enumerate(tracking.get_quiz_review(item["quiz_id"])):
        st.markdown(
            f'<div class="q-label"><span class="q-num">{i + 1:02d}</span>{escape(q["question"])}</div>',
            unsafe_allow_html=True,
        )
        correct = q["options"][q["correct_index"]]
        picked = (q["options"][q["selected_index"]]
                  if q["selected_index"] is not None else "No answer")
        if q["is_correct"]:
            st.markdown(f'<div class="feedback ok">Your answer: {escape(picked)}</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="feedback bad">Your answer: {escape(picked)}<br>'
                f'Correct answer: {escape(correct)}</div>', unsafe_allow_html=True)
        if q["explanation"]:
            st.caption(q["explanation"])


def _section(source: str, kind: str, empty_msg: str, render_item, label):
    items = tracking.list_activity(source, kind)
    if not items:
        theme.empty(empty_msg)
        return
    for item in items:
        with st.expander(f"{_when(item['created_at'])}  |  {label(item)}"):
            render_item(item)


def render():
    sources = vector.list_sources()
    if not sources:
        theme.empty("Upload a document to start building its history.")
        return

    current = st.session_state.get("history_source")
    if current not in sources:
        current = sources[0]
    source = st.selectbox("Document", sources, index=sources.index(current))
    st.session_state.history_source = source

    counts = {k: len(tracking.list_activity(source, k)) for k in ("ask", "notes", "quiz")}
    tab_ask, tab_notes, tab_quiz = st.tabs(
        [f"Questions ({counts['ask']})", f"Notes ({counts['notes']})",
         f"Quizzes ({counts['quiz']})"]
    )
    with tab_ask:
        _section(source, "ask", "No questions asked about this document yet.",
                 _ask_item, lambda i: _short(i["title"]))
    with tab_notes:
        _section(source, "notes", "No notes generated for this document yet.",
                 _notes_item, lambda i: _short(i["title"]))
    with tab_quiz:
        _section(source, "quiz", "No quizzes taken on this document yet.",
                 _quiz_item, lambda i: f"{i['title']}  |  {i['score']}/{i['total']}")
