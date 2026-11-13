import re


def clean_text(text: str) -> str:
    """Normalize raw extracted document text before chunking."""
    text = text.replace("\x00", "")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)      # re-join hyphenated line breaks
    text = re.sub(r"#+ ", "", text)                    # markdown headings
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)       # markdown bold
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
