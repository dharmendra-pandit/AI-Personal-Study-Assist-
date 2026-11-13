import streamlit as st

from src.services import study
from ui.common import run, show_sources


def _show(message: dict):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            show_sources(message["sources"])


def render():
    messages = st.session_state.setdefault("messages", [])

    # History first (oldest at top, newest at bottom), input bar underneath.
    history = st.container()
    with history:
        for m in messages:
            _show(m)

    with st.form("ask_form", clear_on_submit=True, border=False):
        c1, c2 = st.columns([6, 1], vertical_alignment="bottom")
        question = c1.text_input("Question", key="ask_question",
                                 placeholder="Ask about your documents...",
                                 label_visibility="collapsed")
        sent = c2.form_submit_button("Send", type="primary", width="stretch")

    if sent and question.strip():
        user_msg = {"role": "user", "content": question.strip()}
        messages.append(user_msg)
        with history:
            _show(user_msg)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    res = run(study.ask, user_msg["content"])
                if res:
                    st.markdown(res["answer"])
                    show_sources(res["sources"])
                    messages.append({"role": "assistant", "content": res["answer"],
                                     "sources": res["sources"]})
