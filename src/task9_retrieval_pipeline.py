"""Task 9: unified hybrid retrieval with cosine-calibrated fallback."""

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank, rerank_rrf
from .task8_pageindex_vectorless import pageindex_search

SCORE_THRESHOLD = 0.48
DEFAULT_TOP_K = 5
RERANK_METHOD = "rrf"


def retrieve(query: str, top_k: int = DEFAULT_TOP_K, score_threshold: float = SCORE_THRESHOLD, use_reranking: bool = True) -> list[dict]:
    """Run dense+sparse retrieval, fuse/rerank, then use PageIndex fallback.

    ``score_threshold`` is compared only with the original cosine score from
    semantic search; RRF scores are rank-based and must not be used here.
    """
    if not isinstance(query, str) or not query.strip() or top_k <= 0:
        return []
    candidate_k = max(top_k * 2, top_k)
    dense = semantic_search(query, top_k=candidate_k)
    sparse = lexical_search(query, top_k=candidate_k)
    merged = rerank_rrf([dense, sparse], top_k=candidate_k, k=60)
    for item in merged:
        item["source"] = "hybrid"
    final = rerank(query, merged, top_k=top_k, method=RERANK_METHOD) if use_reranking else merged[:top_k]

    best_cosine = dense[0].get("score", 0.0) if dense else 0.0
    if best_cosine < score_threshold:
        fallback = pageindex_search(query, top_k=top_k)
        if fallback:
            return fallback[:top_k]
    return final[:top_k]


if __name__ == "__main__":
    for query in ("lịch trình Hà Giang 3 ngày", "xyzabc123nonsense"):
        print(query, [(r["source"], round(r["score"], 4)) for r in retrieve(query, 3)])
