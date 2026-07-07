import re
from src import config


def chunk_text(text, chunk_size=None, overlap_chars=None):
    if chunk_size is None:
        chunk_size = config.CHUNK_SIZE
    if overlap_chars is None:
        overlap_chars = config.CHUNK_OVERLAP

    paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) < chunk_size or not current:
            if current:
                current += "\n\n" + para
            else:
                current = para
        else:
            chunks.append(current)
            current = para
    if current:
        chunks.append(current)

    result = []
    prev_bengali = ""
    for idx, chunk in enumerate(chunks):
        context = prev_bengali[-overlap_chars:] if prev_bengali else ""
        result.append({
            "idx": idx,
            "text": chunk,
            "context": context,
            "_prev_bengali": None,
        })
        prev_bengali = chunk

    return result
