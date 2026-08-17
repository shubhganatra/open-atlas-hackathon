"""Retrieval with metadata filtering on university + visa_type — the two-bucket
design from the brief. "General" docs (university == "general") always match
regardless of which school is asked about; "any" visa_type docs always match
regardless of visa type. This is the mechanism that has to visibly discriminate
between Texas A&M and Purdue in the demo, not just retrieve generically-similar
text.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.rag.store import get_collection


@dataclass
class RetrievedDoc:
    doc_id: str
    university: str
    topic: str
    source: str
    text: str
    distance: float


def retrieve(
    query: str,
    university: str,
    visa_type: str = "f1",
    topic: str | None = None,
    n_results: int = 3,
) -> list[RetrievedDoc]:
    where_clauses: list[dict] = [
        {"university": {"$in": [university, "general"]}},
        {"visa_type": {"$in": [visa_type, "any"]}},
    ]
    if topic:
        where_clauses.append({"topic": topic})
    where = {"$and": where_clauses} if len(where_clauses) > 1 else where_clauses[0]

    collection = get_collection()
    results = collection.query(query_texts=[query], n_results=n_results, where=where)

    docs: list[RetrievedDoc] = []
    ids = results["ids"][0]
    for i, doc_id in enumerate(ids):
        meta = results["metadatas"][0][i]
        docs.append(
            RetrievedDoc(
                doc_id=doc_id,
                university=meta["university"],
                topic=meta["topic"],
                source=meta["source"],
                text=results["documents"][0][i],
                distance=results["distances"][0][i],
            )
        )
    return docs
