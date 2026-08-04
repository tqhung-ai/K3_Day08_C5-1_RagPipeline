"""Task 5: dense semantic retrieval over the Task 4 Chroma collection."""

import os

import numpy as np

from .task4_chunking_indexing import (
    CHROMA_DIR,
    COLLECTION_NAME,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
)


def _embed_query(query: str) -> list[float]:
    """Embed a query using the same backend used by Task 4.

    Hashing is the default because it is deterministic and works offline with
    the local index generated in this project. Set RAG_USE_BGE=1 to use BGE.
    """
    if os.getenv("RAG_USE_BGE", "").lower() in {"1", "true", "yes"}:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(EMBEDDING_MODEL)
        vector = model.encode([query], normalize_embeddings=True)[0]
        return [float(value) for value in vector.tolist()]

    from sklearn.feature_extraction.text import HashingVectorizer

    vectorizer = HashingVectorizer(
        n_features=EMBEDDING_DIM,
        alternate_sign=False,
        norm="l2",
        ngram_range=(1, 2),
    )
    vector = vectorizer.transform([query]).toarray()[0]
    return [float(value) for value in vector]


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Return top-k chunks ranked by cosine similarity."""
    if not isinstance(query, str) or not query.strip() or top_k <= 0:
        return []
    if not CHROMA_DIR.exists():
        return []

    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        return []

    count = collection.count()
    if count == 0:
        return []
    result = collection.query(
        query_embeddings=[_embed_query(query)],
        n_results=min(int(top_k), count),
        include=["documents", "metadatas", "distances"],
    )

    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    output = []
    for content, metadata, distance in zip(documents, metadatas, distances):
        # Chroma cosine distance is 1 - cosine similarity.
        score = float(np.clip(1.0 - float(distance), 0.0, 1.0))
        output.append({
            "content": content or "",
            "score": round(score, 6),
            "metadata": metadata or {},
        })
    output.sort(key=lambda item: item["score"], reverse=True)
    return output[:top_k]


if __name__ == "__main__":
    for result in semantic_search("lịch trình Hà Giang 3 ngày", top_k=5):
        print(f"[{result['score']:.3f}] {result['content'][:100]}...")
