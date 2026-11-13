"""Study workflows used by the UI: ask, notes, quiz, plan.

`docs` is the user's document selection: a list of file names, or None/[] for all.
Every function raises StudyError with a user-readable message on failure.
"""
from collections import Counter

from src.db import tracking
from src.db.vector import library_overview, list_sources, search
from src.services import ai
from src.services.embedding import get_embeddings
from src.services.retrieval import ask_context, get_context, mentioned_sources


class StudyError(Exception):
    pass


def _llm(fn, *args):
    try:
        return fn(*args)
    except ValueError as e:  # malformed model output
        raise StudyError(str(e)) from e
    except Exception as e:
        raise StudyError(f"LLM request failed: {e}") from e


def _selection(docs: list[str] | None) -> list[str]:
    """The selected documents that still exist; [] means the whole library."""
    library = set(list_sources())
    return [d for d in docs or [] if d in library]


def ask(question: str, docs: list[str] | None = None) -> dict:
    """Answer from the documents named in the question, else the selection, else all."""
    library = list_sources()
    if not library:
        raise StudyError("No documents uploaded yet. Add a PDF or DOCX in the sidebar.")
    contexts = ask_context(question, mentioned_sources(question, library) or _selection(docs))
    if not contexts:
        raise StudyError("No matching passages found in your documents.")
    answer = _llm(ai.generate_answer, question, contexts, library)
    tracking.log_activity(
        "ask", question,
        {"answer": answer,
         "sources": [{"source": c["source"], "page": c["page"], "score": c.get("score"),
                      "text": c["text"][:400]} for c in contexts]},
        [c["source"] for c in contexts],
    )
    return {"answer": answer, "sources": contexts}


def make_notes(topic: str | None, docs: list[str] | None = None, max_chunks: int = 12) -> dict:
    contexts = get_context(topic, _selection(docs), max_chunks)
    if not contexts:
        raise StudyError("No matching documents found.")
    notes = _llm(ai.generate_notes, contexts, topic)
    used = sorted({c["source"] for c in contexts})
    tracking.log_activity("notes", topic or "Whole document",
                          {"notes": notes, "topic": topic}, used)
    return {"notes": notes, "sources": used}


def make_quiz(topic: str | None, docs: list[str] | None, num_questions: int,
              difficulty: str) -> dict:
    selected = _selection(docs)
    contexts = get_context(topic, selected, 12)
    if not contexts:
        raise StudyError("No matching documents found.")
    questions = _llm(ai.generate_quiz, contexts, num_questions, difficulty, topic)
    # credit only the documents the questions actually test, so a quiz that happens to be
    # all about one file does not count towards another file's progress
    offered = {c["source"] for c in contexts}
    tested = {q.source for q in questions if q.source in offered} or offered
    quiz_id = tracking.save_quiz(", ".join(selected) or None, topic, difficulty,
                                 [q.model_dump() for q in questions], sorted(tested))
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


def progress(docs: list[str] | None = None) -> dict:
    """Quiz performance on the selected documents (all when nothing is selected)."""
    return tracking.get_progress(sources=_selection(docs) or None)


def make_plan(days: int, minutes_per_day: int, docs: list[str] | None = None) -> dict:
    selected = _selection(docs)
    prog = tracking.get_progress(sources=selected or None)
    if not prog["attempts"]:
        raise StudyError("Take at least one quiz on the selected documents first, so there "
                         "is performance to plan from." if selected else
                         "Take at least one quiz first so there is performance to plan from.")
    evidence = _plan_evidence(prog, selected)
    plan = _llm(ai.generate_plan, prog, days, minutes_per_day, evidence,
                library_overview(selected or None))
    body = plan.model_dump()
    body["weak_topics"] = [t["topic"] for t in prog["weak_topics"]]
    body["minutes_per_day"] = minutes_per_day
    body["sources"] = selected  # [] = built for the whole library
    tracking.save_plan(body)
    return tracking.get_latest_plan()


def _plan_evidence(prog: dict, docs: list[str], max_topics: int = 5) -> dict:
    """Pull the most relevant passages for each focus topic so the plan can cite real pages."""
    weak = [t["topic"] for t in prog["weak_topics"]]
    lowest = [t["topic"] for t in prog["topics"]]  # weakest first
    stale = [t["topic"] for t in sorted(prog["topics"], key=lambda t: t["last_practiced"])]
    focus = list(dict.fromkeys(weak + lowest[:3] + stale[:2]))[:max_topics]
    if not focus:
        return {}
    vectors = get_embeddings(focus)
    return {
        topic: [{"source": h["source"], "page": h["page"], "excerpt": h["text"][:350]}
                for h in search(vec, 3, docs or None)]
        for topic, vec in zip(focus, vectors)
    }


def _backfill_quiz_sources():
    """Quizzes from before sources were recorded: attribute each to the documents its
    questions match best, so they count towards those documents' progress."""
    for quiz_id, questions in tracking.quizzes_without_sources():
        texts = [f"{q['question']} {' '.join(q['options'])}" for q in questions]
        if not texts:
            continue
        hits = Counter(h[0]["source"] for v in get_embeddings(texts) if (h := search(v, 1)))
        if hits:
            tracking.set_quiz_sources(quiz_id, list(hits))


_backfill_quiz_sources()
