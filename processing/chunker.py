def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    """
    Split text into overlapping word-based chunks.

    Args:
        text:       Input text to chunk.
        chunk_size: Maximum number of words per chunk (default 400).
        overlap:    Number of words to overlap between consecutive chunks (default 50).

    Returns:
        List of non-empty chunk strings.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    step = chunk_size - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk:
            chunks.append(chunk)

    return chunks