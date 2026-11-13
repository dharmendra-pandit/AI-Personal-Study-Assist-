import streamlit as st

from src.services.study import StudyError


def run(fn, *args, **kwargs):
    """Call a study workflow; show a friendly error and return None on failure."""
    try:
        return fn(*args, **kwargs)
    except StudyError as e:
        st.error(str(e))
        return None


def scope_note(docs: list[str] | None, extra: str = ""):
    """One line saying which documents the page works on."""
    using = ", ".join(f"**{d}**" for d in docs) if docs else "**all documents**"
    st.caption(f"Using {using}. {extra}".strip())


def show_sources(sources: list[dict]):
    with st.expander("Sources"):
        for s in sources:
            # chunks sampled for overview questions carry no match score
            score = f", match {s['score']:.2f}" if s.get("score") is not None else ""
            st.markdown(f"**{s['source']}** (page {s['page'] or '-'}{score})")
            st.caption(s["text"])
