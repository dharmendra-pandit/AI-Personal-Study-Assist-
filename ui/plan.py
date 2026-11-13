from datetime import datetime, timedelta
from html import escape

import streamlit as st

from src.db import tracking
from src.services import study
from ui import theme
from ui.common import run

START_LABEL = {"notes": "Open notes", "quiz": "Start quiz", "ask": "Ask now"}


def _start(task: dict):
    """Jump to the right page with the task's topic or question pre-filled."""
    kind = task["type"]
    if kind == "notes":
        st.session_state.notes_topic = task["topic"]
        st.session_state.page = "Notes"
    elif kind == "quiz":
        st.session_state.quiz_topic = task["topic"]
        st.session_state.page = "Quiz"
    elif kind == "ask":
        st.session_state.ask_question = task["description"]
        st.session_state.page = "Ask"


def _toggle(plan_id: int, day: int, idx: int, key: str):
    tracking.set_task_done(plan_id, day, idx, st.session_state[key])


def _start_date(plan: dict):
    try:
        return datetime.fromisoformat(plan["created_at"]).astimezone().date()
    except (KeyError, ValueError):
        return None


def render():
    c1, c2 = st.columns(2)
    days = c1.number_input("Days", 1, 30, 7)
    minutes = c2.number_input("Minutes per day", 10, 480, 45, step=5)

    if st.button("Generate plan from my progress", type="primary"):
        with st.spinner("Building your plan from your results and documents..."):
            plan = run(study.make_plan, int(days), int(minutes))
        if plan:
            st.session_state.plan = plan

    plan = st.session_state.get("plan") or tracking.get_latest_plan()
    if not plan:
        theme.empty("No plan yet. Take a quiz, then generate one.")
        return

    plan_id = plan["plan_id"]
    done = tracking.get_done_tasks(plan_id)
    total_tasks = sum(len(d["tasks"]) for d in plan["days"])
    total_min = sum(t["minutes"] for d in plan["days"] for t in d["tasks"])

    st.markdown(plan["summary"])
    if plan.get("weak_topics"):
        st.caption("Focus areas: " + ", ".join(plan["weak_topics"]))
    st.progress(len(done) / total_tasks if total_tasks else 0,
                text=f"{len(done)} of {total_tasks} tasks done  ·  {total_min} min total")

    # the day to work on now = first day that still has an unfinished task
    current = next((d["day"] for d in plan["days"]
                    if any((d["day"], j) not in done for j in range(len(d["tasks"])))), None)
    start = _start_date(plan)

    for d in plan["days"]:
        day_done = sum((d["day"], j) in done for j in range(len(d["tasks"])))
        minutes_left = sum(t["minutes"] for j, t in enumerate(d["tasks"])
                           if (d["day"], j) not in done)
        when = f"  ·  {(start + timedelta(days=d['day'] - 1)):%a %d %b}" if start else ""
        status = "Complete" if day_done == len(d["tasks"]) else f"{minutes_left} min left"
        title = f"Day {d['day']}{when}  |  {d['focus']}  |  {status}"

        with st.expander(title, expanded=d["day"] == current):
            for j, t in enumerate(d["tasks"]):
                key = f"done_{plan_id}_{d['day']}_{j}"
                check, body, action = st.columns([0.5, 5, 1.4], vertical_alignment="top")
                check.checkbox("Done", value=(d["day"], j) in done, key=key,
                               label_visibility="collapsed",
                               on_change=_toggle, args=(plan_id, d["day"], j, key))

                ref = (f'<div class="task-ref">{escape(t["reference"])}</div>'
                       if t.get("reference") else "")
                outcome = (f'<div class="task-outcome">{escape(t["outcome"])}</div>'
                           if t.get("outcome") else "")
                body.markdown(
                    f'<span class="chip">{t["type"].upper()}</span>'
                    f'<strong>{escape(t["topic"])}</strong> &nbsp;·&nbsp; {t["minutes"]} min'
                    f'<div class="task-desc">{escape(t["description"])}</div>{ref}{outcome}',
                    unsafe_allow_html=True,
                )
                if t["type"] in START_LABEL:
                    action.button(START_LABEL[t["type"]], key=f"go_{plan_id}_{d['day']}_{j}",
                                  on_click=_start, args=(t,), width="stretch")

    st.caption("Tick tasks as you finish them. After a new quiz, generate a fresh plan "
               "so it reflects your latest results.")
