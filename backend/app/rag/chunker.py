def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 50) -> list[str]:
    """
    Split text into overlapping chunks.
    Overlap ensures context isn't lost at chunk boundaries.
    """
    if not text or not text.strip():
        return []

    words = text.split()

    if len(words) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)

        start += chunk_size - overlap

    return chunks