import numpy as np
from sentence_transformers import SentenceTransformer

from src.core.config import EMBEDDING_MODEL

model = SentenceTransformer(EMBEDDING_MODEL)
DIMENSION = model.get_sentence_embedding_dimension()


def get_embeddings(texts: list[str]) -> np.ndarray:
    """Embed a batch of texts -> float32 array of shape (n, DIMENSION), L2-normalized."""
    return model.encode(
        texts, normalize_embeddings=True, convert_to_numpy=True
    ).astype("float32")
