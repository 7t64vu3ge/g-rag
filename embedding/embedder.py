import numpy as np
from fastembed import TextEmbedding

# Load once at module initialisation
_model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")


def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Batch-encode a list of strings into 384-dimensional float32 vectors.

    Args:
        texts: List of text strings to encode.

    Returns:
        numpy array of shape (len(texts), 384), dtype float32.
    """
    return _model.encode(texts, convert_to_numpy=True).astype("float32")


def embed_query(query: str) -> np.ndarray:
    """
    Encode a single query string into a 384-dimensional float32 vector.

    Args:
        query: Query string.

    Returns:
        numpy array of shape (384,), dtype float32.
    """
    return _model.encode([query], convert_to_numpy=True).astype("float32")[0]