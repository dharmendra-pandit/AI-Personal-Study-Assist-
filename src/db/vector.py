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


def _as_set(sources: str | list[str] | None) -> set[str] | None:
    """None or [] means every document; a single name is accepted too."""
    if not sources:
        return None
    return {sources} if isinstance(sources, str) else set(sources)


def search(query_vector: np.ndarray, k: int = 4,
           sources: str | list[str] | None = None) -> list[dict]:
    """Best k matches, optionally only within the given document(s)."""
    wanted = _as_set(sources)
    query_vector = np.asarray(query_vector, dtype="float32").reshape(1, -1)
    with _lock:
        if index.ntotal == 0:
            return []
        # when filtering by source, scan everything then trim (flat index, small scale)
        fetch = index.ntotal if wanted else min(k, index.ntotal)
        scores, ids = index.search(query_vector, fetch)
        results = [
            {**documents[i], "score": float(s)}
            for s, i in zip(scores[0], ids[0])
            if i != -1 and (wanted is None or documents[i]["source"] in wanted)
        ]
        return results[:k]


def _spread(pool: list[dict], n: int) -> list[dict]:
    if len(pool) <= n:
        return pool
    step = len(pool) / n
    return [pool[int(i * step)] for i in range(n)]


def sample_chunks(sources: str | list[str] | None = None, n: int = 10) -> list[dict]:
    """Evenly spaced chunks in document order, for broad coverage (notes / quiz).
    The n slots are shared fairly between documents, so a short file is not drowned out
    by a long one."""
    wanted = _as_set(sources)
    with _lock:
        by_doc: dict[str, list[dict]] = {}
        for d in documents:
            if wanted is None or d["source"] in wanted:
                by_doc.setdefault(d["source"], []).append(d)
    picked: list[dict] = []
    remaining = sorted(by_doc.values(), key=len)  # small docs first; leftovers flow on
    for i, pool in enumerate(remaining):
        share = max(1, (n - len(picked)) // (len(remaining) - i))
        picked.extend(_spread(pool, share))
    return picked[:n]


def list_sources() -> list[str]:
    return sorted({d["source"] for d in documents})


def library_overview(sources: list[str] | None = None) -> list[dict]:
    """Per document: chunk count and page range (None for page-less formats like DOCX)."""
    wanted = _as_set(sources)
    overview: dict[str, dict] = {}
    with _lock:
        for d in documents:
            if wanted is not None and d["source"] not in wanted:
                continue
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
