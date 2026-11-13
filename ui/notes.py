import streamlit as st

from src.services import study
from ui.common import run, scope_note


def render(docs: list[str] | None):
    st.session_state.setdefault("notes", None)
    scope_note(docs)

    topic = st.text_input("Topic", key="notes_topic",
                          placeholder="Optional. Leave blank to cover everything in scope.")
    if st.button("Generate notes", type="primary"):
        with st.spinner("Writing notes..."):
            st.session_state.notes = run(study.make_notes, topic or None, docs)

    notes = st.session_state.notes
    if notes:
        st.divider()
        st.markdown(notes["notes"])
        st.caption("Sources: " + ", ".join(notes["sources"]))
        st.download_button("Download as Markdown", notes["notes"],
                           file_name="notes.md", mime="text/markdown")
