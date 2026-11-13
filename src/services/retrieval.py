import re

from src.core.config import TOP_K
from src.db.vector import sample_chunks, search
from src.services.embedding import get_embeddings


def get_context(topic: str | None, sources: list[str] | None, max_chunks: int) -> list[dict]:
    """Topic given -> semantic search; otherwise evenly sample the document(s).
    `sources` limits both to those documents (None = all)."""
    if topic and topic.strip():
        return search(get_embeddings([topic])[0], max_chunks, sources)
    return sample_chunks(sources, max_chunks)


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def mentioned_sources(question: str, sources: list[str]) -> list[str]:
    """Documents the question names by file name, with or without the extension
    ("aws-overview.pdf", "aws overview")."""
    q = f" {_norm(question)} "
    return [s for s in sources if (stem := _norm(s.rsplit(".", 1)[0])) and f" {stem} " in q]


def ask_context(question: str, docs: list[str] | None = None, k: int = TOP_K) -> list[dict]:
    """Passages for a question. Without `docs`, the best matches across the library.
    With `docs`, each document's best matches plus an even sample of it, so overview
    questions ("what is this file about?") see the whole document, not just one corner."""
    vector = get_embeddings([question])[0]
    if not docs:
        return search(vector, k)
    picked, seen = [], set()
    for doc in docs:
        for chunk in search(vector, k, doc) + sample_chunks(doc, k):
            key = (chunk["source"], chunk["text"])
            if key not in seen:
                seen.add(key)
                picked.append(chunk)
    return picked
