"""Task 4: chunk Markdown documents, embed them and index in ChromaDB."""

import os
from pathlib import Path

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Recursive splitting preserves headings/paragraphs where possible. 800/100 is
# large enough for a travel-guide section while preserving boundary context.
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
CHUNKING_METHOD = "recursive"

# Multilingual model supports Vietnamese and English. It produces 1024-D vectors.
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024
VECTOR_STORE = "chromadb"
COLLECTION_NAME = "university_services_docs"


def load_documents() -> list[dict]:
    """Load non-empty Markdown files with source/type metadata."""
    documents: list[dict] = []
    if not STANDARDIZED_DIR.exists():
        return documents
    for md_file in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8").strip()
        if not content:
            continue
        relative = md_file.relative_to(STANDARDIZED_DIR)
        doc_type = relative.parts[0] if relative.parts else "unknown"
        documents.append({
            "content": content,
            "metadata": {
                "source": md_file.name,
                "type": doc_type,
                "path": str(relative),
            },
        })
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Split documents with RecursiveCharacterTextSplitter."""
    if not documents:
        return []
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        split_fn = splitter.split_text
    except ImportError:
        # Lightweight fallback for environments without LangChain.
        def split_fn(text: str) -> list[str]:
            step = max(1, CHUNK_SIZE - CHUNK_OVERLAP)
            return [text[i:i + CHUNK_SIZE] for i in range(0, len(text), step)]

    chunks: list[dict] = []
    for document in documents:
        for index, text in enumerate(split_fn(document.get("content", ""))):
            text = text.strip()
            if text:
                chunks.append({
                    "content": text,
                    "metadata": {
                        **document.get("metadata", {}),
                        "chunk_index": index,
                    },
                })
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Add normalized sentence-transformer embeddings to every chunk."""
    if not chunks:
        return []
    texts = [chunk["content"] for chunk in chunks]
    try:
        if os.getenv("RAG_OFFLINE", "").lower() in {"1", "true", "yes"}:
            raise RuntimeError("RAG_OFFLINE requested")
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(EMBEDDING_MODEL)
        embeddings = model.encode(
            texts,
            show_progress_bar=True,
            normalize_embeddings=True,
        )
    except Exception as exc:
        # Offline-safe fallback: deterministic 1024-D lexical vectors. This
        # keeps local indexing usable when Hugging Face is unreachable.
        print(f"Warning: {EMBEDDING_MODEL} unavailable ({exc}); using hashing fallback")
        from sklearn.feature_extraction.text import HashingVectorizer
        vectorizer = HashingVectorizer(
            n_features=EMBEDDING_DIM,
            alternate_sign=False,
            norm="l2",
            ngram_range=(1, 2),
        )
        embeddings = vectorizer.transform(texts).toarray()
    for chunk, embedding in zip(chunks, embeddings):
        values = embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)
        chunk["embedding"] = [float(value) for value in values]
    return chunks


def index_to_vectorstore(chunks: list[dict]):
    """Persist embedded chunks in a cosine-distance Chroma collection."""
    if not chunks:
        return None
    if any("embedding" not in chunk for chunk in chunks):
        raise ValueError("Every chunk must have an embedding before indexing")
    if VECTOR_STORE != "chromadb":
        raise ValueError(f"Unsupported vector store: {VECTOR_STORE}")

    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    ids = [
        f"{chunk['metadata'].get('source', 'document')}_chunk_"
        f"{chunk['metadata'].get('chunk_index', i)}"
        for i, chunk in enumerate(chunks)
    ]
    metadatas = [
        {
            key: value
            for key, value in chunk.get("metadata", {}).items()
            if isinstance(value, (str, int, float, bool))
        }
        for chunk in chunks
    ]
    collection.upsert(
        ids=ids,
        documents=[chunk["content"] for chunk in chunks],
        embeddings=[chunk["embedding"] for chunk in chunks],
        metadatas=metadatas,
    )
    return collection


def run_pipeline():
    """Run load -> chunk -> embed -> index."""
    print(f"Chunking: {CHUNKING_METHOD} (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    print(f"Embedding: {EMBEDDING_MODEL} (dim={EMBEDDING_DIM})")
    documents = load_documents()
    print(f"Loaded {len(documents)} documents")
    chunks = chunk_documents(documents)
    print(f"Created {len(chunks)} chunks")
    embedded = embed_chunks(chunks)
    print(f"Embedded {len(embedded)} chunks")
    index_to_vectorstore(embedded)
    print(f"Indexed to {CHROMA_DIR}")


if __name__ == "__main__":
    run_pipeline()
