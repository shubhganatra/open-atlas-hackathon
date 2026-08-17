"""Phase 3 verification: does metadata-filtered retrieval actually discriminate
between schools, and does it correctly pull in general-bucket docs regardless
of school? Run standalone:

    cd backend && .venv/bin/python scripts/verify_rag.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rag.retrieve import retrieve

QUERY = "How do I get a Social Security Number for my on-campus job?"


def _print(label: str, docs) -> None:
    print(f"\n=== {label} ===")
    for d in docs:
        print(f"  [{d.university:10}] {d.doc_id}  (dist={d.distance:.3f})")


def main() -> None:
    am_docs = retrieve(QUERY, university="texas_am", topic="ssn")
    purdue_docs = retrieve(QUERY, university="purdue", topic="ssn")

    _print("Texas A&M SSN query", am_docs)
    _print("Purdue SSN query", purdue_docs)

    # --- The RAG money-shot assertion: same query, different school, DIFFERENT
    # top result — proves metadata filtering discriminates, not just semantic
    # similarity picking whatever's closest across the whole corpus. -----------
    assert am_docs, "expected at least one result for Texas A&M"
    assert purdue_docs, "expected at least one result for Purdue"
    assert am_docs[0].doc_id != purdue_docs[0].doc_id, (
        "Texas A&M and Purdue queries returned the same top doc — "
        "metadata filter isn't discriminating by school"
    )
    assert "texas_am/ssn_on_campus_employment.md" in am_docs[0].doc_id
    assert "purdue/ssn_on_campus_employment.md" in purdue_docs[0].doc_id
    # No cross-contamination: a Purdue query should never surface an A&M-only doc.
    assert all(d.university in ("purdue", "general") for d in purdue_docs)
    assert all(d.university in ("texas_am", "general") for d in am_docs)

    # General bucket should be reachable from either school for a general question.
    general_from_am = retrieve("Do I need an SSN to open a bank account?", university="texas_am")
    _print("Texas A&M general-bucket query", general_from_am)
    assert any(d.university == "general" for d in general_from_am), (
        "expected the general bucket to be reachable when queried through a specific school"
    )

    print("\nAll RAG retrieval assertions passed.")


if __name__ == "__main__":
    main()
