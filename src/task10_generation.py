"""
Task 10 — Generation Có Citation.

Dự án: Trợ Lý Hướng Dẫn Viên Du Lịch Thông Minh
Dữ liệu: Cẩm nang du lịch Việt Nam (Hà Nội, Đà Nẵng, Đà Lạt, Hà Giang...)

Hướng dẫn:
    1. Chọn top_k, top_p phù hợp (giải thích lý do)
    2. Sắp xếp lại chunks sau reranking để tránh "lost in the middle"
    3. Inject context vào prompt
    4. Yêu cầu LLM trả lời có citation
    5. Nếu không đủ evidence → "Tôi không thể xác minh thông tin này từ nguồn hiện có"

Gợi ý LLM: OpenRouter có nhiều model gắn hậu tố ":free" không tính phí — xem
https://openrouter.ai/models?max_price=0 — phù hợp nếu chưa có credit trả phí.
Base URL: "https://openrouter.ai/api/v1", dùng chung interface với OpenAI SDK.
"""

import os
from dotenv import load_dotenv

load_dotenv()

from .task9_retrieval_pipeline import retrieve


# =============================================================================
# CONFIGURATION — Giải thích lựa chọn
# =============================================================================

# top_k: Số chunks đưa vào context
# Chọn 5 vì: đủ evidence mà không quá dài gây lost in the middle
TOP_K = 5

# top_p (nucleus sampling): Xác suất tích luỹ cho token generation
# Chọn 0.9 vì: đủ diverse nhưng không quá random
TOP_P = 0.9

# temperature: Độ ngẫu nhiên của output
# Chọn 0.3 vì: RAG cần factual, ít sáng tạo
TEMPERATURE = 0.3

# LLM model: dùng gpt-4o-mini vì cân bằng tốt giữa chất lượng và chi phí
# Nếu chưa có credit, đổi sang "google/gemma-3-27b-it:free" hoặc "meta-llama/llama-3.3-70b-instruct:free"
LLM_MODEL = "openai/gpt-4o-mini"


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """Bạn là Hướng Dẫn Viên Du Lịch AI thông minh, chuyên cung cấp thông tin
du lịch tự túc chi tiết về các địa phương Việt Nam (lịch trình, ẩm thực, văn hóa, mẹo tiết kiệm).

Quy tắc bắt buộc:
1. Chỉ sử dụng thông tin từ context được cung cấp — KHÔNG bịa đặt địa điểm hay giá cả
2. Mỗi khẳng định phải có trích dẫn ngay sau, ví dụ: [Cẩm nang Hà Giang, 2024] hoặc [Blog du lịch Đà Lạt]
3. Nếu context không đủ thông tin → trả lời: "Tôi không thể xác minh thông tin này từ nguồn hiện có"
4. Trả lời bằng tiếng Việt, có cấu trúc rõ ràng (dùng bullet points, heading khi cần)
5. Không suy luận hay bịa đặt ngoài những gì được nêu rõ trong context
6. Ưu tiên thông tin thực tế: giá tiền, địa chỉ cụ thể, thời gian mở cửa nếu có trong context
7. Khi có lịch sử hội thoại, hãy hiểu câu hỏi hiện tại trong ngữ cảnh cuộc trò chuyện
   (ví dụ: "Vậy ẩm thực ở đó thì sao?" → "đó" chỉ địa điểm đã đề cập trước đó)"""


# =============================================================================
# DOCUMENT REORDERING (tránh lost in the middle)
# =============================================================================

def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """
    Sắp xếp chunks để tránh "lost in the middle" effect.

    LLM nhớ tốt thông tin ở ĐẦU và CUỐI prompt, quên thông tin ở GIỮA.
    Strategy: đặt chunks quan trọng nhất ở đầu và cuối, kém quan trọng ở giữa.

    Input order (by score):  [1, 2, 3, 4, 5]
    Output order:            [1, 3, 5, 4, 2]
    (best first, worst in middle, second-best last)

    Args:
        chunks: List sorted by score descending (from retrieval)

    Returns:
        List reordered để maximize LLM attention.
    """
    # Nếu có <= 2 chunks thì không cần reorder
    if len(chunks) <= 2:
        return chunks

    # Strategy: xen kẽ front + back[::-1]
    # Input (by score desc):  [1, 2, 3, 4, 5]
    # front = [1, 3, 5]  (even index: 0, 2, 4)
    # back  = [2, 4]     (odd index: 1, 3)
    # Output:             [1, 3, 5, 4, 2]
    # → chunk quan trọng nhất (rank 1) ở ĐẦU
    # → chunk quan trọng thứ 2 (rank 2) ở CUỐI
    # → chunk ít quan trọng hơn nằm ở GIỮA (LLM hay bỏ sót)
    front = chunks[::2]   # index 0, 2, 4, ... -> đặt ở đầu
    back = chunks[1::2]   # index 1, 3, ...    -> đặt ở cuối (reversed)
    return front + back[::-1]


# =============================================================================
# CONTEXT FORMATTING
# =============================================================================

def format_context(chunks: list[dict]) -> str:
    """
    Format chunks thành context string cho prompt.
    Mỗi chunk có label source để LLM có thể cite.

    Args:
        chunks: List of {'content': str, 'metadata': dict, 'score': float}

    Returns:
        Formatted context string.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", f"Nguồn {i}")
        doc_type = meta.get("type", "unknown")
        # Label source rõ ràng để LLM có thể cite đúng tên tài liệu
        context_parts.append(
            f"[Tài liệu {i} | Nguồn: {source} | Loại: {doc_type}]\n"
            f"{chunk['content']}\n"
        )
    return "\n---\n".join(context_parts)


# =============================================================================
# GENERATION
# =============================================================================

# Số lượng tin nhắn lịch sử tối đa đưa vào context (N turns = 2*N messages)
# Giữ nhỏ để không vượt context window, đồng thời đủ cho follow-up 2-3 lượt
MAX_HISTORY_TURNS = 3  # = 6 messages (3 user + 3 assistant)


def generate_with_citation(
    query: str,
    top_k: int = TOP_K,
    chat_history: list[dict] | None = None,
) -> dict:
    """
    End-to-end RAG generation có citation + conversation memory.

    Pipeline:
        1. Retrieve relevant chunks
        2. Reorder để tránh lost in the middle
        3. Format context với source labels
        4. Build messages: [system] + [history] + [user với context]
        5. Call LLM
        6. Return answer + sources

    Args:
        query        : Câu hỏi hiện tại của user
        top_k        : Số chunks retrieval
        chat_history : Lịch sử hội thoại — list of {'role': 'user'|'assistant', 'content': str}
                       Truyền None hoặc [] để bỏ qua memory (single-turn mode)

    Returns:
        {
            'answer': str,           # Câu trả lời có citation
            'sources': list[dict],   # Các chunks đã dùng
            'retrieval_source': str  # 'hybrid' hoặc 'pageindex'
        }
    """
    # Step 1: Retrieve chunks từ pipeline (Task 9)
    chunks = retrieve(query, top_k=top_k)

    # Nếu không tìm được chunk nào
    if not chunks:
        return {
            "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có. Vui lòng thử câu hỏi khác.",
            "sources": [],
            "retrieval_source": "none",
        }

    # Step 2: Reorder chunks để tránh lost-in-the-middle
    # Chunk quan trọng nhất → đầu prompt, quan trọng thứ hai → cuối prompt
    reordered = reorder_for_llm(chunks)

    # Step 3: Format context với source labels cho LLM cite
    context = format_context(reordered)

    # Step 4: Build messages list
    # [system] → [history N turns] → [user với RAG context]
    from openai import OpenAI

    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "answer": "❌ Thiếu API key. Vui lòng đặt OPENROUTER_API_KEY trong file .env",
            "sources": chunks,
            "retrieval_source": chunks[0].get("source", "hybrid") if chunks else "none",
        }

    # Bắt đầu messages với system prompt
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Inject lịch sử hội thoại (conversation memory)
    # Giữ MAX_HISTORY_TURNS turns gần nhất để tránh vượt context window
    if chat_history:
        # Mỗi turn = 1 user + 1 assistant message → lấy 2*MAX turns cuối
        recent = chat_history[-(MAX_HISTORY_TURNS * 2):]
        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # Chỉ lấy user và assistant, bỏ qua role khác
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    # User message hiện tại: context RAG + câu hỏi
    user_message = (
        f"Context tài liệu du lịch:\n{context}\n"
        f"\n---\n"
        f"\nCâu hỏi: {query}\n"
        f"\nHãy trả lời dựa HOÀN TOÀN vào context trên. "
        f"Mỗi thông tin phải kèm trích dẫn dạng [Tên nguồn] ngay sau câu đó."
    )
    messages.append({"role": "user", "content": user_message})

    # Step 5: Gọi LLM qua OpenRouter (OpenAI-compatible API)
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=TEMPERATURE,
        top_p=TOP_P,
    )

    answer = response.choices[0].message.content

    # Step 6: Trả về answer + sources để UI hiển thị
    return {
        "answer": answer,
        "sources": chunks,  # chunks gốc (chưa reorder) để hiển thị score đúng
        "retrieval_source": chunks[0].get("source", "hybrid") if chunks else "none",
    }


if __name__ == "__main__":
    # Test queries cho chủ đề Du Lịch Việt Nam
    test_queries = [
        "Gợi ý lịch trình du lịch Hà Giang 3 ngày 2 đêm tự túc bằng xe máy cho người đi lần đầu.",
        "Những món ăn nhất định phải thử khi đến Quy Nhơn và địa chỉ quán ăn chuẩn vị địa phương?",
        "Kinh nghiệm du lịch Đà Lạt tiết kiệm, nên đi mùa nào?",
    ]

    for q in test_queries:
        print(f"\n{'='*70}")
        print(f"Q: {q}")
        print("=" * 70)
        result = generate_with_citation(q)
        print(f"\nA: {result['answer']}")
        print(f"\n[Sources: {len(result['sources'])} chunks | via {result['retrieval_source']}]")
