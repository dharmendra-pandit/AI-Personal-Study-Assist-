import io

import docx
import pdfplumber

from src.core.chunk import chunk_text
from src.core.clean import clean_text
from src.core.config import CHUNK_OVERLAP, CHUNK_SIZE
from src.db.vector import add_vectors
from src.services.embedding import get_embeddings


def read_pdf(file_bytes: bytes) -> list[tuple[int | None, str]]:
    pages = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for n, page in enumerate(pdf.pages, start=1):
            # the default gap tolerance (3) glues words together in tightly spaced PDFs
            # ("FullStackEngineerwitha..."), which ruins search; 1.5 keeps them apart
            pages.append((n, page.extract_text(x_tolerance=1.5) or ""))
    return pages


def read_docx(file_bytes: bytes) -> list[tuple[int | None, str]]:
    doc = docx.Document(io.BytesIO(file_bytes))
    return [(None, "\n".join(p.text for p in doc.paragraphs))]


def ingest_document(filename: str, file_bytes: bytes) -> int:
    """extract -> clean -> chunk -> embed -> store. Returns number of chunks stored."""
    name = filename.lower()
    if name.endswith(".pdf"):
        pages = read_pdf(file_bytes)
    elif name.endswith(".docx"):
        pages = read_docx(file_bytes)
    else:
        raise ValueError("Unsupported file type")

    chunks = []
    for page_no, raw in pages:
        for piece in chunk_text(clean_text(raw), CHUNK_SIZE, CHUNK_OVERLAP):
            chunks.append({"text": piece, "source": filename, "page": page_no})

    if not chunks:
        raise ValueError("No extractable text found (scanned PDF?)")

    add_vectors(get_embeddings([c["text"] for c in chunks]), chunks)
    return len(chunks)
