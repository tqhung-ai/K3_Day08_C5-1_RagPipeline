"""Task 7: reranking utilities (RRF, MMR and safe local fallback)."""

import math
import re


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", (text or "").lower(), flags=re.UNICODE))


def rerank_cross_encoder(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """Offline-safe lexical reranker used when no cross-encoder API is set."""
    query_terms = _tokens(query)
    scored = []
    for candidate in candidates:
        terms = _tokens(candidate.get("content", ""))
        overlap = len(query_terms & terms) / max(1, len(query_terms))
        item = dict(candidate)
        item["score"] = float(overlap)
        scored.append(item)
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:max(0, top_k)]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(float(a[i]) * float(b[i]) for i in range(n))
    na = math.sqrt(sum(float(x) ** 2 for x in a[:n]))
    nb = math.sqrt(sum(float(x) ** 2 for x in b[:n]))
    return dot / (na * nb) if na and nb else 0.0


def rerank_mmr(query_embedding: list[float], candidates: list[dict], top_k: int = 5, lambda_param: float = 0.7) -> list[dict]:
    """Select relevant but diverse candidates with Maximal Marginal Relevance."""
    remaining = list(range(len(candidates)))
    selected: list[int] = []
    while remaining and len(selected) < max(0, top_k):
        best = max(
            remaining,
            key=lambda i: lambda_param * _cosine(query_embedding, candidates[i].get("embedding", []))
            - (1 - lambda_param) * max(
                [_cosine(candidates[i].get("embedding", []), candidates[j].get("embedding", [])) for j in selected],
                default=0.0,
            ),
        )
        selected.append(best)
        remaining.remove(best)
    return [dict(candidates[i]) for i in selected]


def _key(item: dict) -> str:
    metadata = item.get("metadata") or {}
    return "|".join(str(metadata.get(k, "")) for k in ("source", "path", "chunk_index")) or item.get("content", "")


def rerank_rrf(ranked_lists: list[list[dict]], top_k: int = 5, k: int = 60) -> list[dict]:
    """Fuse ranked lists using Reciprocal Rank Fusion with k=60 by default."""
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}
    for ranked_list in ranked_lists or []:
        for rank, item in enumerate(ranked_list or [], start=1):
            key = _key(item)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            # Keep richer metadata/content from the first occurrence.
            items.setdefault(key, dict(item))
    ordered = sorted(scores, key=lambda key: (-scores[key], key))
    output = []
    for key in ordered[:max(0, top_k)]:
        item = dict(items[key])
        item["score"] = float(scores[key])
        output.append(item)
    return output


def rerank(query: str, candidates: list[dict], top_k: int = 5, method: str = "rrf") -> list[dict]:
    if method == "cross_encoder":
        return rerank_cross_encoder(query, candidates, top_k)
    if method == "rrf":
        return rerank_rrf([candidates], top_k=top_k)
    raise ValueError(f"Unknown rerank method: {method}")
