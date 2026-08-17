"""Tiny frontmatter parser for the hand-curated corpus under app/data/corpus/.
Not using a library (e.g. python-frontmatter) on purpose — the format is
`---\\nkey: value\\n---\\nbody`, nothing fancier is needed, and it's one less
dependency to install under a tight clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CORPUS_ROOT = Path(__file__).resolve().parent.parent / "data" / "corpus"


@dataclass
class CorpusDoc:
    doc_id: str  # path relative to CORPUS_ROOT, stable across re-ingests
    university: str
    visa_type: str
    topic: str
    source: str
    body: str


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("expected frontmatter delimited by '---' at top of file")
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    meta = dict(
        (k.strip(), v.strip())
        for k, v in (line.split(":", 1) for line in lines[1:end] if line.strip())
    )
    body = "\n".join(lines[end + 1 :]).strip()
    return meta, body


def load_corpus() -> list[CorpusDoc]:
    docs: list[CorpusDoc] = []
    for path in sorted(CORPUS_ROOT.rglob("*.md")):
        meta, body = _parse_frontmatter(path.read_text())
        docs.append(
            CorpusDoc(
                doc_id=str(path.relative_to(CORPUS_ROOT)),
                university=meta["university"],
                visa_type=meta["visa_type"],
                topic=meta["topic"],
                source=meta["source"],
                body=body,
            )
        )
    return docs
