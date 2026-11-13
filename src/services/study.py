"""Study workflows used by the UI: ask, notes, quiz, plan.

Every function raises StudyError with a user-readable message on failure.
"""
from src.core.config import TOP_K
from src.db import tracking
from src.db.vector import library_overview, search
from src.services import ai
from src.services.embedding import get_embeddings
from src.services.retrieval import get_context


class StudyError(Exception):
    pass


def _llm(fn, *args):
    try:
        return fn(*args)
    except ValueError as e:  # malformed model output
        raise StudyError(str(e)) from e
    except Exception as e:
        raise StudyError(f"LLM request failed: {e}") from e


def ask(question: str) -> dict:
    contexts = search(get_embeddings([question])[0], TOP_K)
    if not contexts:
        raise StudyError("No documents uploaded yet.")
    answer = _llm(ai.generate_answer, question, contexts)
    tracking.log_activity(
        "ask", question,
        {"answer": answer,
         "sources": [{"source": c["source"], "page": c["page"], "score": c["score"],
                      "text": c["text"][:400]} for c in contexts]},
        [c["source"] for c in contexts],
    )
    return {"answer": answer, "sources": contexts}


def make_notes(topic: str | None, source: str | None, max_chunks: int = 12) -> dict:
    contexts = get_context(topic, source, max_chunks)
    if not contexts:
        raise StudyError("No matching documents found.")
    notes = _llm(ai.generate_notes, contexts, topic)
    sources = sorted({c["source"] for c in contexts})
    tracking.log_activity("notes", topic or "Whole document",
                          {"notes": notes, "topic": topic}, sources)
    return {"notes": notes, "sources": sources}


def make_quiz(topic: str | None, source: str | None, num_questions: int,
              difficulty: str) -> dict:
    contexts = get_context(topic, source, 12)
    if not contexts:
        raise StudyError("No matching documents found.")
    questions = _llm(ai.generate_quiz, contexts, num_questions, difficulty, topic)
    quiz_id = tracking.save_quiz(source, topic, difficulty,
                                 [q.model_dump() for q in questions],
                                 sorted({c["source"] for c in contexts}))
    # answers stay in the database until the quiz is submitted
    return {
        "quiz_id": quiz_id,
        "questions": [
            {"question": q.question, "options": q.options, "topic": q.topic}
            for q in questions
        ],
    }


def submit_quiz(quiz_id: int, answers: list[int | None]) -> dict:
    try:
        return tracking.record_attempt(quiz_id, answers)
    except (tracking.QuizNotFound, tracking.AlreadySubmitted, ValueError) as e:
        raise StudyError(str(e)) from e


def make_plan(days: int, minutes_per_day: int) -> dict:
    progress = tracking.get_progress()
    if not progress["attempts"]:
        raise StudyError("Take at least one quiz first so there is performance to plan from.")
    evidence = _plan_evidence(progress)
    plan = _llm(ai.generate_plan, progress, days, minutes_per_day, evidence,
                library_overview())
    body = plan.model_dump()
    body["weak_topics"] = [t["topic"] for t in progress["weak_topics"]]
    body["minutes_per_day"] = minutes_per_day
    tracking.save_plan(body)
    return tracking.get_latest_plan()


def _plan_evidence(progress: dict, max_topics: int = 5) -> dict:
    """Pull the most relevant passages for each focus topic so the plan can cite real pages."""
    weak = [t["topic"] for t in progress["weak_topics"]]
    lowest = [t["topic"] for t in progress["topics"]]  # weakest first
    stale = [t["topic"] for t in sorted(progress["topics"], key=lambda t: t["last_practiced"])]
    focus = list(dict.fromkeys(weak + lowest[:3] + stale[:2]))[:max_topics]
    if not focus:
        return {}
    vectors = get_embeddings(focus)
    return {
        topic: [{"source": h["source"], "page": h["page"], "excerpt": h["text"][:350]}
                for h in search(vec, 3)]
        for topic, vec in zip(focus, vectors)
    }
