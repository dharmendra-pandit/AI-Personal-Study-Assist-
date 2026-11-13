import streamlit as st

from src.db import tracking
from ui import theme


def render():
    prog = tracking.get_progress()

    if not prog["attempts"]:
        theme.empty("No quiz attempts yet. Take a quiz to start tracking your progress.")
        return

    m1, m2, m3 = st.columns(3)
    m1.metric("Quizzes taken", prog["attempts"])
    m2.metric("Questions answered", prog["questions_answered"])
    m3.metric("Overall accuracy", f"{prog['accuracy']:.0%}")

    if prog["weak_topics"]:
        st.warning("Needs attention: " + ", ".join(
            f"{t['topic']} ({t['accuracy']:.0%})" for t in prog["weak_topics"]))
    else:
        st.success("No weak topics at the moment.")

    st.subheader("Accuracy by topic")
    st.bar_chart({t["topic"]: t["accuracy"] for t in prog["topics"]}, horizontal=True,
                 color="#2B3A67")
    st.dataframe(prog["topics"], hide_index=True)

    st.subheader("Recent quizzes")
    st.dataframe(prog["recent_attempts"], hide_index=True)

    if st.button("Reset progress"):
        tracking.reset_progress()
        st.session_state.update(quiz=None, quiz_result=None, plan=None)
        st.rerun()
