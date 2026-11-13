import streamlit as st

from src.services.study import StudyError


def run(fn, *args, **kwargs):
    """Call a study workflow; show a friendly error and return None on failure."""
    try:
        return fn(*args, **kwargs)
    except StudyError as e:
        st.error(str(e))
        return None


def show_sources(sources: list[dict]):
    with st.expander("Sources"):
        for s in sources:
            st.markdown(f"**{s['source']}** (page {s['page'] or '-'}, score {s['score']:.2f})")
            st.caption(s["text"])
