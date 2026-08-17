"""Chroma client + collection setup. One persistent collection, metadata-tagged
per doc (university, visa_type, topic, source) so retrieval can filter without
needing separate collections per school — "two buckets" is a metadata
distinction (university == 'general' vs a specific school), not two physical
stores.
"""

from __future__ import annotations

from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

CHROMA_PATH = Path(__file__).resolve().parent.parent / "data" / "chroma"
COLLECTION_NAME = "onboarding_docs"

_client = None
_collection = None


def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=DefaultEmbeddingFunction(),
        )
    return _collection
