import streamlit as st

from src.db import tracking
from src.services import study
from ui import theme
from ui.common import scope_note


def render(docs: list[str] | None):
    prog = study.progress(docs)
    scope_note(docs, "Counts quizzes drawn from these documents.")

    if not prog["attempts"]:
        theme.empty("No quizzes on the selected documents yet. Take one to start tracking."
                    if docs else
                    "No quiz attempts yet. Take a quiz to start tracking your progress.")
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

    if st.button("Reset all progress", help="Deletes every quiz, result and plan."):
        tracking.reset_progress()
        st.session_state.update(quiz=None, quiz_result=None, plan=None)
        st.rerun()
