from src.db.vector import sample_chunks, search
from src.services.embedding import get_embeddings


def get_context(topic: str | None, source: str | None, max_chunks: int) -> list[dict]:
    """Topic given -> semantic search; otherwise evenly sample the document(s)."""
    if topic and topic.strip():
        return search(get_embeddings([topic])[0], max_chunks, source)
    return sample_chunks(source, max_chunks)
