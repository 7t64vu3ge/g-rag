from embedding.embedder import embed_query
from search import vector_store


def retrieve(query: str, k: int = 5) -> list[dict]:
    """
    Embed a query and return the top-k most relevant chunks from the vector store.

    Args:
        query: Natural-language query string.
        k:     Number of results to return (default 5).

    Returns:
        List of dicts with keys 'text' and 'meta', as returned by vector_store.search().
    """
    query_embedding = embed_query(query)
    return vector_store.search(query_embedding, k=k)
