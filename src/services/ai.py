import json
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

from src.core.config import API_KEY, BASE_URL, LLM_MODEL

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

SYSTEM_PROMPT = (
    "You are a study assistant. Answer the question using ONLY the provided context. "
    "If the context does not contain the answer, say you could not find it in the "
    "uploaded documents. Be accurate and concise."
)

NOTES_PROMPT = (
    "You are a study assistant. Write well-structured study notes using ONLY the provided "
    "context. Use markdown: a title, headings per topic, bullet points, **bold** key terms, "
    "and a short 'Key takeaways' section at the end. Do not add facts that are not in the context."
)

QUIZ_PROMPT = (
    "You are a quiz writer. Using ONLY the provided context, write multiple-choice questions. "
    "Respond with a JSON object of the form: "
    '{"questions": [{"question": str, "options": [4 strings], "answer_index": 0-3, '
    '"explanation": str, "topic": str (2-4 word topic label)}]}. '
    "Exactly one option must be correct, distractors must be plausible, and every question "
    "must be answerable from the context."
)


class QuizQuestion(BaseModel):
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    answer_index: int = Field(ge=0, le=3)
    explanation: str = ""
    topic: str = "General"


class Quiz(BaseModel):
    questions: list[QuizQuestion]


PLAN_PROMPT = (
    "You are a study coach building a practical, concrete plan. You receive the learner's quiz "
    "performance per topic, short evidence excerpts from their own documents (with source file "
    "and page), and a library overview.\n"
    "Rules:\n"
    "1. Weakest topics come first and get the most time. Revisit topics not practiced recently. "
    "Group related topics on the same day. End with one mixed-review day or task.\n"
    "2. Every task must be specific: name the actual concepts to study, drawn from the evidence "
    "excerpts. Never write vague tasks like 'review the topic'.\n"
    "3. 'reference' is where to look, e.g. 'aws-overview.pdf, pp. 12-14'. Use ONLY sources and "
    "pages that appear in the evidence; if none fit, leave it empty. Never invent pages.\n"
    "4. Task types: 'notes' (generate notes on the topic), 'quiz' (take a quiz on the topic), "
    "'review' (re-read the referenced pages and your wrong answers), 'ask' (put one specific "
    "question for the assistant in 'description', phrased as a question).\n"
    "5. 'outcome' is one sentence starting with 'You can' stating what the learner will be able "
    "to do afterwards.\n"
    "6. Tasks are at least 10 minutes; each day's minutes must sum to at most the daily budget.\n"
    "7. If the learner has answered fewer than 10 questions, start with a diagnostic quiz and say "
    "in the summary that the plan will sharpen after more quizzes.\n"
    "8. Keep the summary to two sentences.\n"
    "Respond with a JSON object: "
    '{"summary": str, "days": [{"day": int, "focus": str, "tasks": [{"type": '
    '"notes|quiz|review|ask", "topic": str, "description": str, "reference": str, '
    '"outcome": str, "minutes": int}]}]}.'
)


class PlanTask(BaseModel):
    type: Literal["notes", "quiz", "review", "ask"]
    topic: str
    description: str
    reference: str = ""
    outcome: str = ""
    minutes: int = Field(ge=5, le=240)


class PlanDay(BaseModel):
    day: int = Field(ge=1)
    focus: str
    tasks: list[PlanTask] = Field(min_length=1)


class StudyPlan(BaseModel):
    summary: str
    days: list[PlanDay] = Field(min_length=1)


def _format_context(contexts: list[dict]) -> str:
    return "\n\n".join(
        f"[{i}] ({c['source']}, page {c['page'] or '-'})\n{c['text']}"
        for i, c in enumerate(contexts, start=1)
    )


def _chat(system: str, user: str, temperature: float, json_mode: bool = False) -> str:
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        **kwargs,
    )
    return response.choices[0].message.content


def generate_answer(question: str, contexts: list[dict]) -> str:
    return _chat(
        SYSTEM_PROMPT,
        f"Context:\n{_format_context(contexts)}\n\nQuestion: {question}",
        temperature=0.2,
    )


def generate_notes(contexts: list[dict], topic: str | None = None) -> str:
    focus = f"Focus on: {topic}\n\n" if topic else ""
    return _chat(
        NOTES_PROMPT,
        f"Context:\n{_format_context(contexts)}\n\n{focus}Write the study notes.",
        temperature=0.3,
    )


def generate_plan(progress: dict, days: int, minutes_per_day: int,
                  evidence: dict, library: list[dict]) -> StudyPlan:
    data = {
        "questions_answered": progress["questions_answered"],
        "overall_accuracy": progress["accuracy"],
        "topics": progress["topics"],  # weakest first, with last_practiced timestamps
        "weak_topics": [t["topic"] for t in progress["weak_topics"]],
        "evidence_from_documents": evidence,  # topic -> [{source, page, excerpt}]
        "library": library,
    }
    user = (
        f"Learner data:\n{json.dumps(data, indent=2)}\n\n"
        f"Create a {days}-day plan with a budget of {minutes_per_day} minutes per day."
    )
    last_error = None
    for _ in range(2):
        try:
            raw = _chat(PLAN_PROMPT, user, temperature=0.4, json_mode=True)
            plan = StudyPlan.model_validate(json.loads(raw))
            plan.days = plan.days[:days]
            return plan
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
    raise ValueError(f"Model returned an invalid plan: {last_error}")


def generate_quiz(
    contexts: list[dict], num_questions: int, difficulty: str, topic: str | None = None
) -> list[QuizQuestion]:
    focus = f"Focus on: {topic}\n" if topic else ""
    user = (
        f"Context:\n{_format_context(contexts)}\n\n{focus}"
        f"Write {num_questions} {difficulty} multiple-choice questions."
    )
    last_error = None
    for _ in range(2):  # one retry if the model returns malformed JSON
        try:
            raw = _chat(QUIZ_PROMPT, user, temperature=0.5, json_mode=True)
            return Quiz.model_validate(json.loads(raw)).questions
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
    raise ValueError(f"Model returned an invalid quiz: {last_error}")
