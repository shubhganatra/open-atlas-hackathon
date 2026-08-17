"""Ingest app/data/corpus/**/*.md into the Chroma collection.

    cd backend && .venv/bin/python -m app.rag.ingest

Whole-document chunking (no splitting) — every corpus doc is already a short,
single-topic markdown file, so splitting further would add complexity with no
retrieval-quality benefit at this corpus size. Re-running is idempotent
(upsert, keyed by relative file path).
"""

from __future__ import annotations

from app.rag.corpus_loader import load_corpus
from app.rag.store import get_collection


def ingest() -> int:
    docs = load_corpus()
    collection = get_collection()
    collection.upsert(
        ids=[d.doc_id for d in docs],
        documents=[d.body for d in docs],
        metadatas=[
            {
                "university": d.university,
                "visa_type": d.visa_type,
                "topic": d.topic,
                "source": d.source,
            }
            for d in docs
        ],
    )
    return len(docs)


if __name__ == "__main__":
    n = ingest()
    print(f"Ingested {n} docs into Chroma collection at app/data/chroma/")
