import numpy as np
from sentence_transformers import SentenceTransformer

from src.core.config import EMBEDDING_MODEL


def _load_model() -> SentenceTransformer:
    """Use the locally cached model when available (fast, works offline); download otherwise."""
    try:
        return SentenceTransformer(EMBEDDING_MODEL, local_files_only=True)
    except OSError:
        return SentenceTransformer(EMBEDDING_MODEL)


model = _load_model()
# renamed in sentence-transformers 6; keep the old name working for older installs
_dimension = getattr(model, "get_embedding_dimension", None) or model.get_sentence_embedding_dimension
DIMENSION = _dimension()


def get_embeddings(texts: list[str]) -> np.ndarray:
    """Embed a batch of texts -> float32 array of shape (n, DIMENSION), L2-normalized."""
    return model.encode(
        texts, normalize_embeddings=True, convert_to_numpy=True
    ).astype("float32")
