"""Task 10: citation-aware generation and lost-in-the-middle mitigation."""

import os
from dotenv import load_dotenv

load_dotenv()
from .task9_retrieval_pipeline import retrieve

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3
LLM_MODEL = "openai/gpt-4o-mini"

SYSTEM_PROMPT = """Bạn là trợ lý du lịch Việt Nam. Chỉ sử dụng thông tin trong context.
Mỗi khẳng định phải có citation dạng [Tên nguồn]. Nếu context không đủ, nói:
'Tôi không thể xác minh thông tin này từ nguồn hiện có'. Không được bịa đặt."""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Place important chunks at the beginning/end of the prompt."""
    if len(chunks) <= 2:
        return list(chunks)
    return list(chunks[::2]) + list(chunks[1::2])[::-1]


def format_context(chunks: list[dict]) -> str:
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata") or {}
        source = metadata.get("source") or metadata.get("filename") or f"Nguồn {index}"
        doc_type = metadata.get("type") or metadata.get("category") or "unknown"
        parts.append(f"[Tài liệu {index} | Nguồn: {source} | Loại: {doc_type}]\n{chunk.get('content', '')}")
    return "\n\n---\n\n".join(parts)


def _extractive_answer(chunks: list[dict]) -> str:
    if not chunks:
        return "Tôi không thể xác minh thông tin này từ nguồn hiện có."
    lines = []
    for chunk in chunks[:3]:
        metadata = chunk.get("metadata") or {}
        source = metadata.get("source") or metadata.get("filename") or "Nguồn không xác định"
        content = " ".join(chunk.get("content", "").split())
        if content:
            lines.append(f"- {content[:500]} [{source}]")
    return "\n".join(lines) or "Tôi không thể xác minh thông tin này từ nguồn hiện có."


def generate_with_citation(query: str, top_k: int = TOP_K, chat_history: list[dict] | None = None) -> dict:
    """Retrieve context and generate a cited answer (with offline fallback)."""
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        return {"answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có.", "sources": [], "retrieval_source": "none"}
    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    provider = os.getenv("LLM_PROVIDER", "openrouter").lower()
    openrouter_key = os.getenv("OPENROUTER_API_KEY") if provider != "openai" else None
    openai_key = os.getenv("OPENAI_API_KEY") if provider == "openai" else None
    api_key = openrouter_key or openai_key
    answer = None
    if api_key and os.getenv("RAG_ENABLE_LLM", "").lower() in {"1", "true", "yes"}:
        try:
            from openai import OpenAI
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            if chat_history:
                messages.extend(m for m in chat_history[-6:] if m.get("role") in {"user", "assistant"})
            messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"})
            client = OpenAI(
                api_key=api_key,
                **({"base_url": "https://openrouter.ai/api/v1"} if openrouter_key else {}),
            )
            response = client.chat.completions.create(
                model=LLM_MODEL, messages=messages, temperature=TEMPERATURE, top_p=TOP_P,
            )
            answer = response.choices[0].message.content
        except Exception:
            answer = None
    if not answer:
        answer = _extractive_answer(reordered)
    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": chunks[0].get("source", "hybrid"),
    }
