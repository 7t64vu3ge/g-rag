import os
import logging
import numpy as np
from opensearchpy import OpenSearch, helpers

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenSearch Client Initialisation
# ---------------------------------------------------------------------------
_host = os.environ.get("OPENSEARCH_HOST", "localhost")
_port = os.environ.get("OPENSEARCH_PORT", "9200")
_index_name = os.environ.get("OPENSEARCH_INDEX", "gdrive_docs")

# For local development, we often use 'admin:admin' with security enabled, 
# or no auth if security is disabled.
_client = OpenSearch(
    hosts=[{"host": _host, "port": _port}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False,
)

def _ensure_index():
    """Create the OpenSearch index with k-NN mapping if it doesn't exist."""
    try:
        if not _client.indices.exists(index=_index_name):
            logger.info("Creating OpenSearch index '%s' with k-NN mapping...", _index_name)
            index_body = {
                "settings": {
                    "index": {
                        "knn": True,
                        "knn.algo_param.ef_search": "100"
                    }
                },
                "mappings": {
                    "properties": {
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": 384,
                            "method": {
                                "name": "hnsw",
                                "space_type": "l2",
                                "engine": "nmslib",
                                "parameters": {
                                    "ef_construction": 128,
                                    "m": 16
                                }
                            }
                        },
                        "text": {"type": "text"},
                        "metadata": {"type": "object"}
                    }
                }
            }
            _client.indices.create(index=_index_name, body=index_body)
    except Exception as exc:
        logger.error("Failed to ensure OpenSearch index: %s", exc)

def add(chunks: list[str], embeddings: np.ndarray, metadata: list[dict]) -> None:
    """Bulk index chunks and their embeddings into OpenSearch."""
    _ensure_index()
    
    actions = []
    for i, chunk in enumerate(chunks):
        action = {
            "_index": _index_name,
            "_source": {
                "text": chunk,
                "embedding": embeddings[i].tolist(),
                "metadata": metadata[i]
            }
        }
        actions.append(action)
    
    try:
        success, failed = helpers.bulk(_client, actions)
        logger.info("Indexed %d documents into OpenSearch (failed: %d).", success, failed)
    except Exception as exc:
        logger.error("Bulk indexing failed: %s", exc)

def search(query_embedding: np.ndarray, k: int = 5) -> list[dict]:
    """Perform k-NN search in OpenSearch."""
    _ensure_index()

    query = {
        "size": k,
        "query": {
            "knn": {
                "embedding": {
                    "vector": query_embedding.tolist(),
                    "k": k
                }
            }
        }
    }

    try:
        response = _client.search(index=_index_name, body=query)
        hits = response["hits"]["hits"]
        
        results = []
        for hit in hits:
            results.append({
                "text": hit["_source"]["text"],
                "meta": hit["_source"]["metadata"]
            })
        return results
    except Exception as exc:
        logger.error("OpenSearch search failed: %s", exc)
        return []