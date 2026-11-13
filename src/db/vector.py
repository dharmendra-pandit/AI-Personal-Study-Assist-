import json
import threading

import faiss
import numpy as np

from src.core.config import CHUNKS_PATH, INDEX_PATH
from src.services.embedding import DIMENSION

_lock = threading.Lock()

# vectors are normalized, so inner product == cosine similarity
index = faiss.IndexFlatIP(DIMENSION)
# one metadata dict per vector: {"text", "source", "page"}
documents: list[dict] = []


def _load():
    global index, documents
    if INDEX_PATH.exists() and CHUNKS_PATH.exists():
        index = faiss.read_index(str(INDEX_PATH))
        documents = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))


def _save():
    faiss.write_index(index, str(INDEX_PATH))
    CHUNKS_PATH.write_text(json.dumps(documents, ensure_ascii=False), encoding="utf-8")


def add_vectors(vectors: np.ndarray, chunks: list[dict]):
    """Store chunks; any earlier copy of the same document(s) is replaced, not duplicated."""
    global documents
    with _lock:
        names = {c["source"] for c in chunks}
        stale = [i for i, d in enumerate(documents) if d["source"] in names]
        if stale:
            # a flat index compacts on removal, keeping the remaining vectors in order
            index.remove_ids(np.array(stale, dtype="int64"))
            documents = [d for d in documents if d["source"] not in names]
        index.add(np.asarray(vectors, dtype="float32"))
        documents.extend(chunks)
        _save()


def search(query_vector: np.ndarray, k: int = 4, source: str | None = None) -> list[dict]:
    query_vector = np.asarray(query_vector, dtype="float32").reshape(1, -1)
    with _lock:
        if index.ntotal == 0:
            return []
        # when filtering by source, scan everything then trim (flat index, small scale)
        fetch = index.ntotal if source else min(k, index.ntotal)
        scores, ids = index.search(query_vector, fetch)
        results = [
            {**documents[i], "score": float(s)}
            for s, i in zip(scores[0], ids[0])
            if i != -1 and (source is None or documents[i]["source"] == source)
        ]
        return results[:k]


def sample_chunks(source: str | None = None, n: int = 10) -> list[dict]:
    """Evenly spaced chunks in document order, for broad coverage (notes / quiz)."""
    with _lock:
        pool = [d for d in documents if source is None or d["source"] == source]
    if len(pool) <= n:
        return pool
    step = len(pool) / n
    return [pool[int(i * step)] for i in range(n)]


def list_sources() -> list[str]:
    return sorted({d["source"] for d in documents})


def library_overview() -> list[dict]:
    """Per document: chunk count and page range (None for page-less formats like DOCX)."""
    overview: dict[str, dict] = {}
    with _lock:
        for d in documents:
            o = overview.setdefault(d["source"], {"source": d["source"], "chunks": 0, "pages": set()})
            o["chunks"] += 1
            if d["page"]:
                o["pages"].add(d["page"])
    return [
        {"source": o["source"], "chunks": o["chunks"],
         "page_range": [min(o["pages"]), max(o["pages"])] if o["pages"] else None}
        for o in overview.values()
    ]


def count() -> int:
    return index.ntotal


def reset():
    global index, documents
    with _lock:
        index = faiss.IndexFlatIP(DIMENSION)
        documents = []
        _save()


_load()
