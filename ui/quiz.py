from html import escape

import streamlit as st

from src.services import study
from ui.common import run, scope_note


def _reset_answers():
    for k in [k for k in st.session_state if k.startswith("q_")]:
        del st.session_state[k]


def render(docs: list[str] | None):
    st.session_state.setdefault("quiz", None)
    scope_note(docs)
    st.session_state.setdefault("quiz_result", None)

    c1, c2, c3 = st.columns([3, 1, 1])
    topic = c1.text_input("Topic", key="quiz_topic", placeholder="Optional")
    num_q = c2.number_input("Questions", 1, 20, 5)
    difficulty = c3.selectbox("Difficulty", ["easy", "medium", "hard"], index=1)

    if st.button("Generate quiz", type="primary"):
        with st.spinner("Writing questions..."):
            quiz = run(study.make_quiz, topic or None, docs, int(num_q), difficulty)
        if quiz:
            _reset_answers()
            st.session_state.quiz = quiz
            st.session_state.quiz_result = None

    quiz = st.session_state.quiz
    if not quiz:
        return
    result = st.session_state.quiz_result
    st.divider()

    for i, q in enumerate(quiz["questions"]):
        st.markdown(
            f'<div class="q-label"><span class="q-num">{i + 1:02d}</span>{escape(q["question"])}</div>',
            unsafe_allow_html=True,
        )
        st.radio("Answer", q["options"], index=None, key=f"q_{i}",
                 disabled=result is not None, label_visibility="collapsed")
        if result:
            r = result["results"][i]
            if r["is_correct"]:
                st.markdown('<div class="feedback ok">Correct</div>', unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<div class="feedback bad">Incorrect. Answer: '
                    f'{escape(r["options"][r["correct_index"]])}</div>',
                    unsafe_allow_html=True,
                )
            if r["explanation"]:
                st.caption(r["explanation"])

    if result:
        st.markdown(f'<div class="score">{result["score"]} / {result["total"]}</div>',
                    unsafe_allow_html=True)
        st.caption("Saved to your progress.")
    elif st.button("Submit answers", type="primary"):
        answers = []
        for i, q in enumerate(quiz["questions"]):
            choice = st.session_state.get(f"q_{i}")
            answers.append(q["options"].index(choice) if choice else None)
        res = run(study.submit_quiz, quiz["quiz_id"], answers)
        if res:
            st.session_state.quiz_result = res
            st.rerun()
