import streamlit as st

from src.services import study
from ui.common import scope_note, show_sources


def _source_line(sources: list[dict]) -> str:
    """'From a.pdf (p. 2, 5) · b.docx' for the documents an answer drew on."""
    pages: dict[str, set] = {}
    for s in sources:
        pages.setdefault(s["source"], set()).update([s["page"]] if s.get("page") else [])
    return "From " + "  ·  ".join(
        f"{name} (p. {', '.join(map(str, sorted(p)))})" if p else name
        for name, p in pages.items()
    )


def _body(message: dict):
    if message.get("error"):
        st.warning(message["content"])
        return
    st.markdown(message["content"])
    if message.get("sources"):
        st.caption(_source_line(message["sources"]))
        show_sources(message["sources"])


def _show(message: dict):
    with st.chat_message(message["role"]):
        _body(message)


def _reply(question: str, docs: list[str] | None) -> dict:
    try:
        res = study.ask(question, docs)
    except study.StudyError as e:
        return {"role": "assistant", "content": str(e), "error": True}
    return {"role": "assistant", "content": res["answer"], "sources": res["sources"]}


def render(docs: list[str] | None):
    messages = st.session_state.setdefault("messages", [])

    info, clear = st.columns([5, 1], vertical_alignment="center")
    with info:
        scope_note(docs, "Tick documents in the sidebar, or name a file in your question.")
    if messages and clear.button("Clear chat", type="tertiary", width="stretch"):
        messages.clear()
        st.rerun()

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

    question = question.strip()
    if sent and question:
        user_msg = {"role": "user", "content": question}
        with history:
            _show(user_msg)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    reply = _reply(question, docs)
                    # Save before drawing anything: a second click or Enter while the
                    # answer is being written restarts the page, which would drop it.
                    messages.extend([user_msg, reply])
                _body(reply)
