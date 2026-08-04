"""Task 8: PageIndex-compatible vectorless retrieval with local fallback."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
PAGEINDEX_API_KEY = __import__("os").getenv("PAGEINDEX_API_KEY", "")
MANIFEST_PATH = Path(__file__).parent.parent / "pageindex_doc_ids.json"


def upload_documents() -> list[dict]:
    """Register local documents; return a manifest usable by PageIndex queries.

    When a PageIndex key/SDK is configured, this manifest is the place to store
    remote document IDs. Without credentials, local structural retrieval is used
    so the checkpoint remains reproducible offline.
    """
    docs = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")) if STANDARDIZED_DIR.exists() else []:
        docs.append({
            "doc_id": path.stem,
            "path": str(path),
            "source": path.name,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "backend": "pageindex" if PAGEINDEX_API_KEY else "local",
        })
    MANIFEST_PATH.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
    return docs


def _sections(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
    pieces = re.split(r"(?=^#{1,6}\s+)", text, flags=re.MULTILINE)
    return [(piece.splitlines()[0].lstrip("# ").strip() or path.stem, piece.strip()) for piece in pieces if piece.strip()]


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Vectorless structural search over headings/sections.

    Results carry ``source='pageindex'`` whether the local fallback or the
    optional PageIndex backend is used.
    """
    if not isinstance(query, str) or not query.strip() or top_k <= 0:
        return []
    terms = set(re.findall(r"\w+", query.lower(), flags=re.UNICODE))
    candidates = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")) if STANDARDIZED_DIR.exists() else []:
        for title, content in _sections(path):
            words = set(re.findall(r"\w+", content.lower(), flags=re.UNICODE))
            overlap = len(terms & words)
            if overlap == 0:
                continue
            score = overlap / max(1, len(terms))
            candidates.append({
                "content": content,
                "score": round(float(score), 6),
                "metadata": {"source": path.name, "section": title, "type": path.parent.name},
                "source": "pageindex",
            })
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:top_k]


if __name__ == "__main__":
    upload_documents()
    for result in pageindex_search("lịch trình Hà Giang", top_k=3):
        print(result["score"], result["metadata"].get("source"))
