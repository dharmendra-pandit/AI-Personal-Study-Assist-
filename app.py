"""Personal AI Study Assistant — run with:  streamlit run app.py"""
import streamlit as st

st.set_page_config(page_title="Study Assistant", layout="centered")

from ui import chat, history, notes, plan, progress, quiz, sidebar, theme  # noqa: E402

PAGES = {
    "Ask": lambda source: chat.render(),
    "Notes": notes.render,
    "Quiz": quiz.render,
    "Progress": lambda source: progress.render(),
    "Plan": lambda source: plan.render(),
    "History": lambda source: history.render(),
}

# Widgets on pages that are not shown lose their state; re-assigning keeps it alive
# so topics, typed questions and quiz answers survive switching pages.
for key in list(st.session_state):
    if key in ("notes_topic", "quiz_topic", "ask_question") or key.startswith("q_"):
        st.session_state[key] = st.session_state[key]

theme.apply()
st.markdown(
    '<div class="app-title">Study Assistant</div>'
    '<div class="app-sub">Learn from your own documents: ask, summarize, practice, improve.</div>',
    unsafe_allow_html=True,
)

source = sidebar.render()

st.session_state.setdefault("page", "Ask")
st.segmented_control("Navigate", list(PAGES), key="page", label_visibility="collapsed")
st.divider()

PAGES[st.session_state.get("page") or "Ask"](source)
