"""Personal AI Study Assistant — run with:  .\\run.bat  (or streamlit run app.py inside myenv)"""
import importlib.util
import sys

import streamlit as st

st.set_page_config(page_title="Study Assistant", layout="centered")

# A plain `streamlit run` outside the virtual environment picks up the global Python, which
# usually lacks these. Say so clearly instead of failing with a ModuleNotFoundError.
REQUIRED = {"faiss": "faiss-cpu", "sentence_transformers": "sentence-transformers",
            "openai": "openai", "pydantic": "pydantic", "dotenv": "python-dotenv",
            "pdfplumber": "pdfplumber", "docx": "python-docx"}
missing = [pkg for mod, pkg in REQUIRED.items() if importlib.util.find_spec(mod) is None]
if missing:
    st.error(
        f"Missing packages: {', '.join(missing)}.\n\n"
        f"The app is running on `{sys.executable}`, which is probably not the project's "
        "virtual environment. Stop it (Ctrl+C in the terminal) and start it with "
        "`.\\run.bat`, or activate the environment first: `.\\myenv\\Scripts\\Activate.ps1`, "
        "then `streamlit run app.py`.\n\n"
        "If you are already in the environment, install them with "
        "`pip install -r requirements.txt`."
    )
    st.stop()

# The first import loads torch and the embedding model, which can take a while; later
# reruns reuse the loaded modules and skip this.
with st.spinner("Loading the study engine. The first start can take a minute..."):
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
