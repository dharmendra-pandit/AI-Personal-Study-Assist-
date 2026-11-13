import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from src.core.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS quizzes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at     TEXT NOT NULL,
    source         TEXT,
    topic          TEXT,
    difficulty     TEXT NOT NULL,
    questions_json TEXT NOT NULL,
    sources_json   TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS attempts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id    INTEGER NOT NULL UNIQUE REFERENCES quizzes(id),
    created_at TEXT NOT NULL,
    score      INTEGER NOT NULL,
    total      INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS results (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id     INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
    topic          TEXT NOT NULL,
    question       TEXT NOT NULL,
    selected_index INTEGER,
    correct_index  INTEGER NOT NULL,
    is_correct     INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS plans (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    plan_json  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS activity (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at   TEXT NOT NULL,
    kind         TEXT NOT NULL,          -- 'ask' | 'notes' | 'quiz'
    title        TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS activity_sources (
    activity_id INTEGER NOT NULL REFERENCES activity(id) ON DELETE CASCADE,
    source      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_activity_sources ON activity_sources(source);
CREATE TABLE IF NOT EXISTS task_status (
    plan_id  INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    day      INTEGER NOT NULL,
    task_idx INTEGER NOT NULL,
    PRIMARY KEY (plan_id, day, task_idx)
);
"""


class QuizNotFound(Exception):
    pass


class AlreadySubmitted(Exception):
    pass


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_topic(topic: str) -> str:
    """Collapse whitespace and capitalize the first letter, keeping acronyms (EC2, IPO) intact."""
    topic = " ".join(topic.split())
    return topic[:1].upper() + topic[1:] if topic else "General"


def init_db():
    with closing(_conn()) as conn, conn:
        conn.executescript(SCHEMA)
        # databases created before sources were tracked
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(quizzes)")}
        if "sources_json" not in cols:
            conn.execute("ALTER TABLE quizzes ADD COLUMN sources_json TEXT NOT NULL DEFAULT '[]'")


def _log(conn: sqlite3.Connection, kind: str, title: str, payload: dict, sources: list[str]):
    cur = conn.execute(
        "INSERT INTO activity (created_at, kind, title, payload_json) VALUES (?, ?, ?, ?)",
        (_now(), kind, title, json.dumps(payload)),
    )
    conn.executemany("INSERT INTO activity_sources (activity_id, source) VALUES (?, ?)",
                     [(cur.lastrowid, s) for s in sorted(set(sources))])


def log_activity(kind: str, title: str, payload: dict, sources: list[str]):
    """Record an ask / notes event so it shows up in each document's history."""
    with closing(_conn()) as conn, conn:
        _log(conn, kind, title, payload, sources)


def list_activity(source: str, kind: str, limit: int = 100) -> list[dict]:
    """History for one document and kind, newest first."""
    with closing(_conn()) as conn:
        rows = conn.execute(
            "SELECT a.id, a.created_at, a.title, a.payload_json FROM activity a "
            "JOIN activity_sources s ON s.activity_id = a.id "
            "WHERE s.source = ? AND a.kind = ? ORDER BY a.id DESC LIMIT ?",
            (source, kind, limit),
        ).fetchall()
    return [{"id": r["id"], "created_at": r["created_at"], "title": r["title"],
             **json.loads(r["payload_json"])} for r in rows]


def get_quiz_review(quiz_id: int) -> list[dict]:
    """A submitted quiz with the learner's answers, for the history view."""
    with closing(_conn()) as conn:
        quiz = conn.execute("SELECT questions_json FROM quizzes WHERE id = ?",
                            (quiz_id,)).fetchone()
        rows = conn.execute(
            "SELECT r.selected_index, r.is_correct FROM results r "
            "JOIN attempts a ON a.id = r.attempt_id WHERE a.quiz_id = ? ORDER BY r.id",
            (quiz_id,),
        ).fetchall()
    if quiz is None:
        return []
    return [
        {"question": q["question"], "options": q["options"], "topic": q["topic"],
         "correct_index": q["answer_index"], "explanation": q.get("explanation", ""),
         "selected_index": r["selected_index"], "is_correct": bool(r["is_correct"])}
        for q, r in zip(json.loads(quiz["questions_json"]), rows)
    ]


def save_quiz(source: str | None, topic: str | None, difficulty: str,
              questions: list[dict], sources: list[str] | None = None) -> int:
    """Store the full quiz (with answers) server-side; the client only gets the id."""
    with closing(_conn()) as conn, conn:
        cur = conn.execute(
            "INSERT INTO quizzes (created_at, source, topic, difficulty, questions_json, "
            "sources_json) VALUES (?, ?, ?, ?, ?, ?)",
            (_now(), source, topic, difficulty, json.dumps(questions),
             json.dumps(sources or [])),
        )
        return cur.lastrowid


def record_attempt(quiz_id: int, answers: list[int | None]) -> dict:
    """Grade answers against the stored quiz and persist the attempt."""
    with closing(_conn()) as conn, conn:
        row = conn.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()
        if row is None:
            raise QuizNotFound(f"Quiz {quiz_id} not found")
        questions = json.loads(row["questions_json"])
        if len(answers) != len(questions):
            raise ValueError(f"Expected {len(questions)} answers, got {len(answers)}")

        results = []
        for q, selected in zip(questions, answers):
            valid = selected is not None and 0 <= selected < len(q["options"])
            selected = selected if valid else None
            results.append({
                "question": q["question"],
                "topic": normalize_topic(q["topic"]),
                "options": q["options"],
                "selected_index": selected,
                "correct_index": q["answer_index"],
                "is_correct": selected == q["answer_index"],
                "explanation": q.get("explanation", ""),
            })
        score = sum(r["is_correct"] for r in results)

        try:
            cur = conn.execute(
                "INSERT INTO attempts (quiz_id, created_at, score, total) VALUES (?, ?, ?, ?)",
                (quiz_id, _now(), score, len(results)),
            )
        except sqlite3.IntegrityError:
            raise AlreadySubmitted(f"Quiz {quiz_id} was already submitted")
        conn.executemany(
            "INSERT INTO results (attempt_id, topic, question, selected_index, "
            "correct_index, is_correct) VALUES (?, ?, ?, ?, ?, ?)",
            [(cur.lastrowid, r["topic"], r["question"], r["selected_index"],
              r["correct_index"], int(r["is_correct"])) for r in results],
        )
        label = f"{row['difficulty'].title()} quiz" + (f" on {row['topic']}" if row["topic"] else "")
        _log(conn, "quiz", label,
             {"quiz_id": quiz_id, "attempt_id": cur.lastrowid, "score": score,
              "total": len(results), "difficulty": row["difficulty"], "topic": row["topic"]},
             json.loads(row["sources_json"]))
    return {"attempt_id": cur.lastrowid, "score": score, "total": len(results),
            "results": results}


def quizzes_without_sources() -> list[tuple[int, list[dict]]]:
    """Quizzes saved before their source documents were recorded."""
    with closing(_conn()) as conn:
        rows = conn.execute("SELECT id, questions_json FROM quizzes "
                            "WHERE sources_json = '[]'").fetchall()
    return [(r["id"], json.loads(r["questions_json"])) for r in rows]


def set_quiz_sources(quiz_id: int, sources: list[str]):
    with closing(_conn()) as conn, conn:
        conn.execute("UPDATE quizzes SET sources_json = ? WHERE id = ?",
                     (json.dumps(sorted(set(sources))), quiz_id))


def _in_scope(sources: list[str] | None) -> tuple[str, list[str]]:
    """SQL condition on attempts `a`: the quiz drew on at least one of `sources`."""
    if not sources:
        return "1 = 1", []
    marks = ", ".join("?" * len(sources))
    return (f"a.quiz_id IN (SELECT q2.id FROM quizzes q2, json_each(q2.sources_json) j "
            f"WHERE j.value IN ({marks}))", list(sources))


def get_progress(weak_threshold: float = 0.7, min_questions: int = 2,
                 sources: list[str] | None = None) -> dict:
    """Quiz performance, limited to quizzes on `sources` when given (None = everything)."""
    scope, params = _in_scope(sources)
    with closing(_conn()) as conn:
        overall = conn.execute(
            "SELECT COUNT(DISTINCT r.attempt_id) AS attempts, COUNT(*) AS questions, "
            "COALESCE(SUM(r.is_correct), 0) AS correct "
            f"FROM results r JOIN attempts a ON a.id = r.attempt_id WHERE {scope}", params
        ).fetchone()
        topic_rows = conn.execute(
            "SELECT MIN(r.topic) AS topic, COUNT(*) AS total, SUM(r.is_correct) AS correct, "
            "MAX(a.created_at) AS last_practiced "
            f"FROM results r JOIN attempts a ON a.id = r.attempt_id WHERE {scope} "
            "GROUP BY LOWER(r.topic)", params
        ).fetchall()
        recent = conn.execute(
            "SELECT a.id, a.created_at, a.score, a.total, q.sources_json, q.topic, q.difficulty "
            f"FROM attempts a JOIN quizzes q ON q.id = a.quiz_id WHERE {scope} "
            "ORDER BY a.id DESC LIMIT 10", params
        ).fetchall()

    topics = sorted(
        ({"topic": r["topic"], "total": r["total"], "correct": r["correct"],
          "accuracy": round(r["correct"] / r["total"], 3),
          "last_practiced": r["last_practiced"]} for r in topic_rows),
        key=lambda t: t["accuracy"],
    )
    return {
        "attempts": overall["attempts"],
        "questions_answered": overall["questions"],
        "accuracy": round(overall["correct"] / overall["questions"], 3)
        if overall["questions"] else None,
        "topics": topics,  # weakest first
        "weak_topics": [t for t in topics
                        if t["total"] >= min_questions and t["accuracy"] < weak_threshold],
        "recent_attempts": [
            {"id": r["id"], "created_at": r["created_at"], "score": r["score"],
             "total": r["total"], "documents": ", ".join(json.loads(r["sources_json"])),
             "topic": r["topic"], "difficulty": r["difficulty"]}
            for r in recent
        ],
    }


def save_plan(plan: dict) -> int:
    with closing(_conn()) as conn, conn:
        cur = conn.execute(
            "INSERT INTO plans (created_at, plan_json) VALUES (?, ?)",
            (_now(), json.dumps(plan)),
        )
        return cur.lastrowid


def get_latest_plan() -> dict | None:
    with closing(_conn()) as conn:
        row = conn.execute("SELECT * FROM plans ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        return None
    return {"plan_id": row["id"], "created_at": row["created_at"],
            **json.loads(row["plan_json"])}


def set_task_done(plan_id: int, day: int, task_idx: int, done: bool):
    with closing(_conn()) as conn, conn:
        if done:
            conn.execute("INSERT OR IGNORE INTO task_status (plan_id, day, task_idx) "
                         "VALUES (?, ?, ?)", (plan_id, day, task_idx))
        else:
            conn.execute("DELETE FROM task_status WHERE plan_id = ? AND day = ? "
                         "AND task_idx = ?", (plan_id, day, task_idx))


def get_done_tasks(plan_id: int) -> set[tuple[int, int]]:
    with closing(_conn()) as conn:
        rows = conn.execute("SELECT day, task_idx FROM task_status WHERE plan_id = ?",
                            (plan_id,)).fetchall()
    return {(r["day"], r["task_idx"]) for r in rows}


def reset_progress():
    with closing(_conn()) as conn, conn:
        conn.executescript(
            "DELETE FROM activity WHERE kind = 'quiz'; "
            "DELETE FROM task_status; DELETE FROM results; DELETE FROM attempts; "
            "DELETE FROM quizzes; DELETE FROM plans;"
        )


init_db()
