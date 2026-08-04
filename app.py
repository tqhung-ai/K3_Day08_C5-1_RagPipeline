"""
Trợ Lý Hướng Dẫn Viên Du Lịch Thông Minh
Streamlit Chatbot kết nối RAG Retrieval (Task 9) và Generation có Citation (Task 10).

Chủ đề: Du lịch tự túc Việt Nam — lịch trình, ẩm thực, văn hóa, mẹo tiết kiệm.

Chạy:
    streamlit run app.py
"""

import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Thêm project root vào sys.path để import các task từ src/
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Trợ Lý Du Lịch Việt Nam 🏍️",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# CUSTOM CSS — Premium Vietnamese Travel Theme
# =============================================================================

st.markdown("""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');

/* ── Root Variables — LIGHT THEME ── */
:root {
    --primary:      #d63031;
    --secondary:    #e17055;
    --accent:       #f39c12;
    --text-main:    #1a1a2e;
    --text-sub:     #3d3d5c;
    --text-muted:   #6b7280;
    --bg-main:      #f8f9fa;
    --bg-card:      #ffffff;
    --bg-card2:     #f1f3f8;
    --border:       rgba(0,0,0,0.10);
    --border-accent:rgba(214,48,49,0.30);
    --radius:       12px;
    --shadow:       0 2px 12px rgba(0,0,0,0.08);
}

/* ── Global font & base text ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    font-size: 16px;
}
p, li, span, label { font-size: 1rem; }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }

/* ── Main background ── */
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"] {
    background: var(--bg-main) !important;
}
.main .block-container {
    padding-top: 1.5rem;
    max-width: 920px;
    background: var(--bg-main) !important;
}

/* ── Sidebar: keep dark purple for contrast ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1040 0%, #2d1b69 55%, #1e1245 100%) !important;
    border-right: 2px solid rgba(214,48,49,0.25);
}
[data-testid="stSidebar"],
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] label {
    color: #f0f0f0 !important;
    font-size: 0.95rem !important;
}

/* ── Sidebar title ── */
.sidebar-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.5rem !important;
    font-weight: 700;
    background: linear-gradient(135deg, #ffd700, #ff7f50);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.3rem;
}
.sidebar-subtitle {
    font-size: 0.85rem !important;
    color: rgba(230,230,255,0.75) !important;
    line-height: 1.6;
}

/* ── Suggestion buttons ── */
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.10) !important;
    border: 1px solid rgba(255,255,255,0.22) !important;
    color: #f0f0f0 !important;
    border-radius: 8px !important;
    font-size: 0.88rem !important;
    text-align: left !important;
    padding: 0.55rem 0.85rem !important;
    transition: all 0.2s ease !important;
    white-space: normal !important;
    height: auto !important;
    line-height: 1.45 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(214,48,49,0.30) !important;
    border-color: #ff7f50 !important;
    transform: translateX(3px);
    color: #fff !important;
}

/* ── Sidebar slider & toggle ── */
[data-testid="stSlider"] label,
[data-testid="stToggle"] label,
[data-testid="stSlider"] p,
[data-testid="stToggle"] p {
    font-size: 0.9rem !important;
    color: #e0e0f5 !important;
}

/* ── Architecture chip ── */
.arch-chip {
    display: block;
    background: rgba(255,215,0,0.10);
    border: 1px solid rgba(255,215,0,0.28);
    border-radius: 8px;
    padding: 0.6rem 0.9rem;
    font-size: 0.82rem !important;
    color: #ffd700 !important;
    line-height: 1.8;
    margin-top: 0.5rem;
    width: 100%;
    box-sizing: border-box;
}

/* ── Hero header ── */
.hero-header {
    text-align: center;
    padding: 1.5rem 0 0.75rem;
}
.hero-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.4rem;
    font-weight: 700;
    background: linear-gradient(135deg, #d63031 0%, #e17055 50%, #f39c12 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.2;
    margin-bottom: 0.5rem;
}
.hero-subtitle {
    font-size: 1rem;
    color: var(--text-sub) !important;
    font-weight: 500;
}

/* ── Location tags ── */
.tag-row {
    display: flex;
    gap: 0.5rem;
    justify-content: center;
    flex-wrap: wrap;
    margin-top: 0.85rem;
}
.tag {
    background: #fff;
    border: 1.5px solid rgba(214,48,49,0.25);
    border-radius: 20px;
    padding: 0.25rem 0.9rem;
    font-size: 0.85rem;
    color: var(--text-sub) !important;
    font-weight: 600;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

/* ── Welcome card ── */
.welcome-card {
    background: linear-gradient(135deg, rgba(214,48,49,0.06), rgba(225,112,85,0.04));
    border: 1.5px solid rgba(214,48,49,0.22);
    border-radius: var(--radius);
    padding: 1.75rem 2rem;
    margin-bottom: 1.25rem;
    text-align: center;
    box-shadow: var(--shadow);
}
.welcome-emoji { font-size: 3rem; }
.welcome-text {
    font-size: 1rem;
    color: var(--text-sub) !important;
    margin-top: 0.75rem;
    line-height: 1.75;
}
.welcome-text strong { color: var(--primary) !important; }
.welcome-text em { color: #e17055 !important; font-style: normal; font-weight: 600; }

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    border-radius: var(--radius) !important;
    border: 1px solid var(--border) !important;
    background: var(--bg-card) !important;
    margin-bottom: 0.85rem;
    box-shadow: var(--shadow);
    animation: fadeInUp 0.3s ease;
}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] li {
    color: var(--text-main) !important;
    font-size: 1rem !important;
    line-height: 1.75 !important;
}
/* User bubble accent */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: linear-gradient(135deg, #fff5f5, #fff8f6) !important;
    border-color: rgba(214,48,49,0.20) !important;
}
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── Source expander ── */
[data-testid="stExpander"] {
    background: var(--bg-card2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    box-shadow: none !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] p,
[data-testid="stExpander"] span {
    color: var(--text-main) !important;
    font-size: 0.95rem !important;
}

/* ── Source card ── */
.source-card {
    background: #ffffff;
    border: 1.5px solid rgba(214,48,49,0.15);
    border-radius: 8px;
    padding: 0.7rem 1rem;
    margin-bottom: 0.6rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.source-label {
    font-size: 0.88rem;
    font-weight: 700;
    color: var(--primary) !important;
}
.source-meta {
    font-size: 0.82rem;
    color: var(--text-muted) !important;
    margin-top: 0.15rem;
}

/* ── Retrieval badges ── */
[data-testid="stSlider"] label,
[data-testid="stToggle"] label,
[data-testid="stSlider"] p,
[data-testid="stToggle"] p {
    font-size: 0.82rem !important;
    color: #e8e8f0 !important;
}

/* ── Divider ── */
hr { border-color: rgba(0,0,0,0.10) !important; }

/* ── Chat input ── */
[data-testid="stChatInput"] textarea {
    color: #1a1a2e !important;
    font-size: 1rem !important;
    background: #ffffff !important;
}
[data-testid="stChatInputContainer"],
[data-testid="stChatInput"] > div {
    border-radius: var(--radius) !important;
    border: 1.5px solid rgba(214,48,49,0.35) !important;
    background: #ffffff !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
}
[data-testid="stChatInput"] > div:focus-within {
    border-color: #d63031 !important;
    box-shadow: 0 0 0 3px rgba(214,48,49,0.12) !important;
}

/* ── Welcome card (override cũ) ── */
.welcome-card {
    background: linear-gradient(135deg, rgba(214,48,49,0.07), rgba(225,112,85,0.04));
    border: 1.5px solid rgba(214,48,49,0.22);
    border-radius: var(--radius);
    padding: 1.75rem 2rem;
    margin-bottom: 1.25rem;
    text-align: center;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07);
}
.welcome-emoji { font-size: 3rem; }
.welcome-text {
    font-size: 1.05rem;
    color: #1a1a2e !important;
    margin-top: 0.75rem;
    line-height: 1.8;
    font-weight: 400;
}
.welcome-text strong {
    color: #d63031 !important;
    font-weight: 700;
}
.welcome-text em {
    color: #e17055 !important;
    font-style: normal;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown('<div class="sidebar-title">🗺️ Du Lịch Việt Nam</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sidebar-subtitle">Trợ lý hướng dẫn viên AI — lịch trình, ẩm thực, '
        'văn hóa ứng xử và mẹo tiết kiệm chi phí cho 63 tỉnh thành.</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Câu hỏi gợi ý ──
    st.markdown("**💡 Câu hỏi gợi ý**")
    suggestions = [
        "🏍️ Gợi ý lịch trình Hà Giang 3 ngày 2 đêm tự túc bằng xe máy",
        "🦞 Những món ăn phải thử khi đến Quy Nhơn + địa chỉ quán chuẩn vị",
        "🌸 Kinh nghiệm du lịch Đà Lạt tiết kiệm — nên đi mùa nào?",
        "🏖️ Lịch trình Đà Nẵng 4 ngày 3 đêm cho gia đình có trẻ nhỏ",
        "🌿 Khám phá Sapa tháng mấy đẹp nhất, chi phí tự túc bao nhiêu?",
        "🍜 Phố ẩm thực Hà Nội nên ăn gì buổi sáng, trưa, tối?",
    ]
    for s in suggestions:
        if st.button(s, use_container_width=True, key=f"sug_{s[:25]}"):
            st.session_state["pending_query"] = s

    st.divider()

    # ── Thiết lập ──
    st.markdown("**⚙️ Thiết lập**")
    top_k = st.slider("Số chunks retrieval (top_k)", 3, 10, 5)
    show_score = st.toggle("Hiển thị điểm relevance", value=True)
    show_content = st.toggle("Hiển thị nội dung chunks", value=False)

    st.divider()

    # ── Nút xóa lịch sử ──
    if st.button("🗑️ Xóa lịch sử hội thoại", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    # ── Kiến trúc ──
    st.markdown(
        '<div class="arch-chip">'
        "🔍 Hybrid Retrieval (Semantic + BM25)<br>"
        "⚖️ RRF Rerank + PageIndex Fallback<br>"
        "📝 Document Reordering (Lost-in-Middle)<br>"
        "🔖 LLM Generation có Citation"
        "</div>",
        unsafe_allow_html=True,
    )

# =============================================================================
# SESSION STATE
# =============================================================================

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

# =============================================================================
# MAIN AREA — HERO HEADER
# =============================================================================

st.markdown("""
<div class="hero-header">
    <div class="hero-title">🏍️ Trợ Lý Hướng Dẫn Viên Du Lịch AI</div>
    <div class="hero-subtitle">Thông tin du lịch tự túc Việt Nam • Lịch trình • Ẩm thực • Văn hóa • Mẹo tiết kiệm</div>
    <div class="tag-row">
        <span class="tag">🏔️ Hà Giang</span>
        <span class="tag">🌊 Đà Nẵng</span>
        <span class="tag">🌸 Đà Lạt</span>
        <span class="tag">🏖️ Quy Nhơn</span>
        <span class="tag">🌿 Sapa</span>
        <span class="tag">🏛️ Hà Nội</span>
    </div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# CHAT HISTORY
# =============================================================================

# Welcome card khi chưa có tin nhắn
if not st.session_state.messages:
    st.markdown("""
    <div class="welcome-card">
        <div class="welcome-emoji">🗺️</div>
        <div class="welcome-text">
            Xin chào! Tôi là <strong>Trợ Lý Du Lịch AI</strong> được hỗ trợ bởi RAG Pipeline.<br>
            Hãy hỏi tôi về <strong>lịch trình, ẩm thực, văn hóa</strong> và <strong>mẹo tiết kiệm</strong>
            cho bất kỳ địa phương nào ở Việt Nam.<br>
            <em>Mọi câu trả lời đều có trích dẫn nguồn rõ ràng để bạn kiểm chứng! 🔖</em>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Hiển thị lịch sử
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🗺️"):
        st.markdown(msg["content"])
        # Hiển thị sources cho assistant messages
        if msg["role"] == "assistant" and msg.get("sources"):
            sources = msg["sources"]
            retrieval_src = msg.get("retrieval_source", "hybrid")
            badge_cls = {
                "hybrid": "badge-hybrid",
                "pageindex": "badge-pageindex",
            }.get(retrieval_src, "badge-none")

            with st.expander(f"📚 Nguồn tham khảo ({len(sources)} chunks)"):
                st.markdown(
                    f'<span class="{badge_cls}">● {retrieval_src.upper()}</span> &nbsp;'
                    f"<small style='color:#888'>retrieval source</small>",
                    unsafe_allow_html=True,
                )
                st.markdown("---")
                for i, src in enumerate(sources, 1):
                    meta = src.get("metadata", {})
                    source_name = meta.get("source", "Unknown")
                    doc_type = meta.get("type", "unknown")
                    score = src.get("score", 0)

                    # Source card
                    score_html = f"| score: `{score:.4f}`" if show_score else ""
                    st.markdown(
                        f'<div class="source-card">'
                        f'<div class="source-label">[{i}] {source_name}</div>'
                        f'<div class="source-meta">Loại: {doc_type} {score_html}</div>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    if show_content:
                        snippet = src.get("content", "")[:400]
                        st.caption(snippet + ("..." if len(src.get("content", "")) > 400 else ""))

# =============================================================================
# QUERY HANDLING
# =============================================================================

user_input = st.chat_input("💬 Hỏi về du lịch Việt Nam... (lịch trình, ẩm thực, mẹo tiết kiệm)")
query = user_input or st.session_state.pending_query

if query:
    # Xóa pending và strip emoji từ suggestions nếu có
    st.session_state.pending_query = None
    # Loại bỏ emoji đầu dòng từ suggestions (vd: "🏍️ Gợi ý...")
    clean_query = query.strip()
    if len(clean_query) > 3 and clean_query[1] in ("️", "🏍", "🌸", "🦞", "🏖", "🌿", "🍜"):
        # Bỏ emoji + space đầu
        parts = clean_query.split(" ", 1)
        if len(parts) == 2:
            clean_query = parts[1]

    # Hiển thị câu hỏi user
    st.session_state.messages.append({"role": "user", "content": clean_query})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(clean_query)

    # Sinh câu trả lời
    with st.chat_message("assistant", avatar="🗺️"):
        with st.spinner("🔍 Đang tìm kiếm tài liệu và tổng hợp câu trả lời..."):
            try:
                import importlib, sys
                # Force reload để tránh dùng module cache cũ khi file vừa được cập nhật
                for mod_name in list(sys.modules.keys()):
                    if mod_name.startswith("src."):
                        importlib.reload(sys.modules[mod_name])

                from src.task10_generation import generate_with_citation

                # Pass lịch sử chat (trừ tin nhắn user vừa thêm ở trên) để làm memory
                history = st.session_state.messages[:-1]
                response = generate_with_citation(clean_query, top_k=top_k, chat_history=history)
                answer = response.get("answer", "Chưa thể trả lời.")
                sources = response.get("sources", [])
                retrieval_source = response.get("retrieval_source", "hybrid")

            except NotImplementedError as e:
                err_msg = str(e).lower()
                # Bắt lỗi từ bất kỳ task nào trong pipeline (Task 5 → 9)
                pipeline_keywords = [
                    "retrieve", "semantic", "lexical", "rerank", "bm25",
                    "pageindex", "search", "chunk", "embed", "index",
                ]
                is_pipeline_error = any(kw in err_msg for kw in pipeline_keywords)
                if is_pipeline_error:
                    # Xác định task nào đang bị block
                    if "semantic" in err_msg or "embed" in err_msg:
                        missing = "Task 5 (Semantic Search)"
                    elif "lexical" in err_msg or "bm25" in err_msg:
                        missing = "Task 6 (Lexical/BM25 Search)"
                    elif "rerank" in err_msg:
                        missing = "Task 7 (Reranking)"
                    elif "pageindex" in err_msg:
                        missing = "Task 8 (PageIndex Fallback)"
                    elif "retrieve" in err_msg:
                        missing = "Task 9 (Retrieval Pipeline)"
                    else:
                        missing = "một task trong pipeline (Task 5–9)"
                    answer = (
                        f"⏳ **Pipeline chưa sẵn sàng — đang chờ {missing}**\n\n"
                        "Chatbot UI **(Task 10 + app.py)** của Role 5 đã hoàn chỉnh "
                        "và sẵn sàng kết nối khi nhóm implement xong các task còn lại.\n\n"
                        f"*Chi tiết lỗi: `{e}`*"
                    )
                else:
                    answer = (
                        "⚠️ **Task 10 chưa được implement.**\n\n"
                        "Hãy hoàn thành `src/task10_generation.py` để kết nối pipeline vào UI!"
                    )
                sources = []
                retrieval_source = "none"
            except Exception as e:
                answer = f"❌ **Lỗi khi chạy RAG Pipeline:** `{e}`"
                sources = []
                retrieval_source = "none"

        # Hiển thị answer
        st.markdown(answer)

        # Hiển thị sources
        if sources:
            badge_cls = {
                "hybrid": "badge-hybrid",
                "pageindex": "badge-pageindex",
            }.get(retrieval_source, "badge-none")

            with st.expander(f"📚 Nguồn tham khảo ({len(sources)} chunks)"):
                st.markdown(
                    f'<span class="{badge_cls}">● {retrieval_source.upper()}</span> &nbsp;'
                    f"<small style='color:#888'>retrieval source</small>",
                    unsafe_allow_html=True,
                )
                st.markdown("---")
                for i, src in enumerate(sources, 1):
                    meta = src.get("metadata", {})
                    source_name = meta.get("source", "Unknown")
                    doc_type = meta.get("type", "unknown")
                    score = src.get("score", 0)

                    score_html = f"| score: `{score:.4f}`" if show_score else ""
                    st.markdown(
                        f'<div class="source-card">'
                        f'<div class="source-label">[{i}] {source_name}</div>'
                        f'<div class="source-meta">Loại: {doc_type} {score_html}</div>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    if show_content:
                        snippet = src.get("content", "")[:400]
                        st.caption(snippet + ("..." if len(src.get("content", "")) > 400 else ""))

    # Lưu vào history
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
        "retrieval_source": retrieval_source,
    })
