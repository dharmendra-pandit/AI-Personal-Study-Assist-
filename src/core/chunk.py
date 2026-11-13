import re

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def _split_units(text: str, chunk_size: int) -> list[str]:
    """Break text into sentence-ish units, hard-splitting any that exceed chunk_size."""
    units = []
    for part in _SENTENCE_SPLIT.split(text):
        part = part.strip()
        if not part:
            continue
        while len(part) > chunk_size:
            units.append(part[:chunk_size])
            part = part[chunk_size:]
        units.append(part)
    return units


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    """Pack sentences into chunks of ~chunk_size chars, carrying `overlap` chars forward."""
    chunks: list[str] = []
    current: list[str] = []
    length = 0

    for unit in _split_units(text, chunk_size):
        if current and length + len(unit) + 1 > chunk_size:
            chunks.append(" ".join(current))
            # keep trailing sentences as overlap for the next chunk
            tail, tail_len = [], 0
            for s in reversed(current):
                if tail_len + len(s) > overlap:
                    break
                tail.insert(0, s)
                tail_len += len(s) + 1
            current, length = tail, tail_len
        current.append(unit)
        length += len(unit) + 1

    if current:
        chunks.append(" ".join(current))
    return chunks
