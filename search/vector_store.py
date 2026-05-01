import numpy as np
import faiss

# FAISS index: L2 distance, 384 dimensions (all-MiniLM-L6-v2 output size)
_index = faiss.IndexFlatL2(384)

_chunks_store: list[str] = []
_metadata_store: list[dict] = []


def add(chunks: list[str], embeddings: np.ndarray, metadata: list[dict]) -> None:
    """Add chunks and their embeddings to the in-memory FAISS index."""
    _index.add(np.array(embeddings).astype("float32"))
    _chunks_store.extend(chunks)
    _metadata_store.extend(metadata)


def search(query_embedding: np.ndarray, k: int = 5) -> list[dict]:
    """Perform L2 similarity search in the FAISS index."""
    total = _index.ntotal
    if total == 0:
        return []

    effective_k = min(k, total)
    _, indices = _index.search(
        np.array([query_embedding]).astype("float32"), effective_k
    )

    results = []
    for idx in indices[0]:
        if idx == -1:
            continue
        results.append({
            "text": _chunks_store[idx],
            "meta": _metadata_store[idx],
        })

    return results