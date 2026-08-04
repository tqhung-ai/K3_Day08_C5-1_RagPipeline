from __future__ import annotations

import importlib
import importlib.util
import inspect
import os
import time
from collections.abc import Callable, Sequence
from typing import Any

import streamlit as st


APP_TITLE = "Trợ Lý Hướng Dẫn Viên Du Lịch Thông Minh"
APP_ICON = "🧳"

SUGGESTED_QUESTIONS = [
    "Gợi ý lịch trình Hà Giang 3 ngày 2 đêm cho người đi lần đầu.",
    "Những món ăn nên thử khi đến Hà Nội là gì?",
    "Các địa điểm nổi bật khi du lịch Đà Nẵng.",
    "Tôi cần chuẩn bị gì cho chuyến đi Ninh Bình tự túc?",
    "Khi tham quan đền chùa, du khách cần lưu ý điều gì?",
    "Gợi ý trải nghiệm văn hóa phù hợp khi đến Hội An.",
]

TASK9_MODULE = "src.task9_retrieval_pipeline"
TASK10_MODULE = "src.task10_generation"

TASK9_FUNCTION_CANDIDATES = (
    "retrieval_pipeline",
    "run_retrieval_pipeline",
    "retrieve",
    "hybrid_search",
    "search",
    "run_pipeline",
)

TASK10_FUNCTION_CANDIDATES = (
    "generate_with_citation",
    "generate_with_citations",
    "generate_answer",
    "generate_response",
    "answer_with_citations",
    "generate",
)


def _configure_page() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1120px;
            padding-top: 1.6rem;
            padding-bottom: 4rem;
        }
        .app-subtitle {
            color: #5f6b7a;
            margin-top: -0.6rem;
            margin-bottom: 1.2rem;
        }
        .status-card {
            border: 1px solid rgba(120, 120, 120, 0.22);
            border-radius: 0.75rem;
            padding: 0.75rem 0.9rem;
            margin-bottom: 0.8rem;
        }
        .source-caption {
            color: #667085;
            font-size: 0.88rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Xin chào! Mình có thể hỗ trợ tra cứu lịch trình, "
                    "địa điểm, ẩm thực và lưu ý du lịch dựa trên bộ tài liệu "
                    "của nhóm."
                ),
                "sources": [],
                "latency_seconds": None,
            }
        ]

    if "last_error" not in st.session_state:
        st.session_state.last_error = None


def _module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, AttributeError, ValueError):
        return False


def _find_callable(
    module: Any,
    candidates: Sequence[str],
) -> tuple[str, Callable[..., Any]]:
    for name in candidates:
        value = getattr(module, name, None)
        if callable(value):
            return name, value

    public_functions = [
        name
        for name, value in inspect.getmembers(module, inspect.isfunction)
        if not name.startswith("_")
    ]

    raise RuntimeError(
        f"Không tìm thấy hàm phù hợp trong {module.__name__}. "
        f"Các hàm hiện có: {public_functions or 'không có'}."
    )


def _invoke_query_function(
    function: Callable[..., Any],
    query: str,
    top_k: int,
) -> Any:
    """
    Gọi hàm retrieval với nhiều dạng chữ ký phổ biến.

    Ưu tiên keyword để tránh nhầm thứ tự tham số.
    """
    attempts = [
        lambda: function(query=query, top_k=top_k),
        lambda: function(question=query, top_k=top_k),
        lambda: function(query, top_k),
        lambda: function(query=query),
        lambda: function(question=query),
        lambda: function(query),
    ]

    last_error: TypeError | None = None

    for attempt in attempts:
        try:
            return attempt()
        except TypeError as exc:
            last_error = exc

    raise RuntimeError(
        "Không gọi được hàm Task 9 với các chữ ký phổ biến. "
        f"Lỗi gần nhất: {last_error}"
    )


def _invoke_generation_function(
    function: Callable[..., Any],
    query: str,
    contexts: list[dict[str, Any]],
) -> Any:
    """
    Gọi hàm generation với nhiều contract thường gặp.
    """
    attempts = [
        lambda: function(query=query, contexts=contexts),
        lambda: function(question=query, contexts=contexts),
        lambda: function(query=query, retrieved_contexts=contexts),
        lambda: function(question=query, retrieved_contexts=contexts),
        lambda: function(query, contexts),
        lambda: function(contexts, query),
    ]

    last_error: TypeError | None = None

    for attempt in attempts:
        try:
            return attempt()
        except TypeError as exc:
            last_error = exc

    raise RuntimeError(
        "Không gọi được hàm Task 10. Hàm cần nhận câu hỏi và contexts. "
        f"Lỗi gần nhất: {last_error}"
    )


def _first_nonempty(
    mapping: dict[str, Any],
    keys: Sequence[str],
) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _normalise_context(
    item: Any,
    index: int,
) -> dict[str, Any]:
    if isinstance(item, str):
        return {
            "content": item.strip(),
            "score": None,
            "metadata": {
                "source": f"context_{index}",
            },
        }

    if not isinstance(item, dict):
        return {
            "content": str(item).strip(),
            "score": None,
            "metadata": {
                "source": f"context_{index}",
            },
        }

    metadata = item.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    for key in (
        "source",
        "source_path",
        "title",
        "page",
        "section",
        "chunk_index",
        "retrieval_method",
    ):
        if key in item and key not in metadata:
            metadata[key] = item[key]

    content = _first_nonempty(
        item,
        (
            "content",
            "text",
            "document",
            "passage",
            "excerpt",
            "page_content",
        ),
    )

    raw_score = item.get("score")
    try:
        score = float(raw_score) if raw_score is not None else None
    except (TypeError, ValueError):
        score = None

    return {
        "content": str(content or "").strip(),
        "score": score,
        "metadata": metadata,
    }


def _extract_contexts(
    retrieval_output: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Chuẩn hóa đầu ra Task 9.

    Hỗ trợ:
    - list[dict]
    - {"results": [...]}
    - {"contexts": [...]}
    - {"documents": [...]}
    - {"retrieved_documents": [...]}
    """
    retrieval_metadata: dict[str, Any] = {}

    if retrieval_output is None:
        raw_contexts: Any = []
    elif isinstance(retrieval_output, list):
        raw_contexts = retrieval_output
    elif isinstance(retrieval_output, tuple):
        raw_contexts = list(retrieval_output)
    elif isinstance(retrieval_output, dict):
        raw_contexts = _first_nonempty(
            retrieval_output,
            (
                "results",
                "contexts",
                "documents",
                "retrieved_documents",
                "reranked_results",
                "final_results",
                "sources",
            ),
        )

        retrieval_metadata = {
            key: value
            for key, value in retrieval_output.items()
            if key
            not in {
                "results",
                "contexts",
                "documents",
                "retrieved_documents",
                "reranked_results",
                "final_results",
                "sources",
            }
        }

        if raw_contexts is None:
            # Một số pipeline trả thẳng một context dict.
            if any(
                key in retrieval_output
                for key in ("content", "text", "document", "passage")
            ):
                raw_contexts = [retrieval_output]
            else:
                raw_contexts = []
    else:
        raw_contexts = [retrieval_output]

    if not isinstance(raw_contexts, list):
        raw_contexts = [raw_contexts]

    contexts = [
        _normalise_context(item, index)
        for index, item in enumerate(raw_contexts, start=1)
    ]

    contexts = [
        context
        for context in contexts
        if context["content"]
    ]

    return contexts, retrieval_metadata


def _extract_answer(
    generation_output: Any,
) -> tuple[str, dict[str, Any]]:
    if isinstance(generation_output, str):
        return generation_output.strip(), {}

    if isinstance(generation_output, dict):
        answer = _first_nonempty(
            generation_output,
            (
                "answer",
                "response",
                "content",
                "text",
                "generated_answer",
            ),
        )

        metadata = {
            key: value
            for key, value in generation_output.items()
            if key
            not in {
                "answer",
                "response",
                "content",
                "text",
                "generated_answer",
                "contexts",
            }
        }

        if answer is None:
            return str(generation_output), metadata

        return str(answer).strip(), metadata

    content = getattr(generation_output, "content", None)
    if content is not None:
        return str(content).strip(), {}

    return str(generation_output).strip(), {}


def run_rag(
    query: str,
    top_k: int,
) -> dict[str, Any]:
    """
    Task 9 -> Task 10.
    """
    task9 = importlib.import_module(TASK9_MODULE)
    task10 = importlib.import_module(TASK10_MODULE)

    task9_name, task9_function = _find_callable(
        task9,
        TASK9_FUNCTION_CANDIDATES,
    )
    task10_name, task10_function = _find_callable(
        task10,
        TASK10_FUNCTION_CANDIDATES,
    )

    retrieval_output = _invoke_query_function(
        task9_function,
        query,
        top_k,
    )
    contexts, retrieval_metadata = _extract_contexts(
        retrieval_output
    )

    generation_output = _invoke_generation_function(
        task10_function,
        query,
        contexts,
    )
    answer, generation_metadata = _extract_answer(
        generation_output
    )

    if not answer:
        raise RuntimeError(
            "Task 10 trả về câu trả lời rỗng."
        )

    return {
        "answer": answer,
        "contexts": contexts,
        "retrieval_metadata": retrieval_metadata,
        "generation_metadata": generation_metadata,
        "task9_function": task9_name,
        "task10_function": task10_name,
    }


def _source_name(
    metadata: dict[str, Any],
    index: int,
) -> str:
    return str(
        metadata.get("title")
        or metadata.get("source")
        or metadata.get("source_path")
        or f"Tài liệu {index}"
    )


def _render_sources(
    contexts: Sequence[dict[str, Any]],
    *,
    expanded: bool = False,
) -> None:
    if not contexts:
        st.caption("Không có tài liệu tham khảo được trả về.")
        return

    unique_sources = {
        _source_name(context.get("metadata", {}), index)
        for index, context in enumerate(contexts, start=1)
    }

    st.caption(
        f"{len(contexts)} đoạn tham khảo từ "
        f"{len(unique_sources)} nguồn."
    )

    for index, context in enumerate(contexts, start=1):
        metadata = context.get("metadata", {})
        source = _source_name(metadata, index)
        page = metadata.get("page")
        section = metadata.get("section")
        chunk_index = metadata.get("chunk_index")
        retrieval_method = metadata.get("retrieval_method")
        score = context.get("score")

        label_parts = [f"[{index}] {source}"]

        if page not in (None, ""):
            label_parts.append(f"trang {page}")

        if score is not None:
            label_parts.append(f"score {score:.3f}")

        with st.expander(
            " · ".join(label_parts),
            expanded=expanded,
        ):
            detail_columns = st.columns(3)

            detail_columns[0].caption(
                f"Section: {section or 'N/A'}"
            )
            detail_columns[1].caption(
                f"Chunk: {chunk_index if chunk_index is not None else 'N/A'}"
            )
            detail_columns[2].caption(
                f"Retriever: {retrieval_method or 'N/A'}"
            )

            st.markdown(context.get("content", ""))


def _render_message(message: dict[str, Any]) -> None:
    role = message.get("role", "assistant")
    avatar = "🧑" if role == "user" else APP_ICON

    with st.chat_message(role, avatar=avatar):
        st.markdown(message.get("content", ""))

        if role == "assistant":
            latency = message.get("latency_seconds")
            if latency is not None:
                st.caption(f"Thời gian xử lý: {latency:.2f} giây")

            sources = message.get("sources") or []
            if sources:
                with st.expander(
                    f"📚 Tài liệu tham khảo ({len(sources)})",
                    expanded=False,
                ):
                    _render_sources(sources)


def _render_sidebar() -> tuple[int, bool]:
    with st.sidebar:
        st.header("⚙️ Cài đặt")

        top_k = st.slider(
            "Số đoạn tài liệu truy xuất (`top_k`)",
            min_value=1,
            max_value=10,
            value=5,
            step=1,
            help=(
                "Số context tối đa được chuyển từ retrieval "
                "sang bước sinh câu trả lời."
            ),
        )

        show_sources = st.toggle(
            "Tự động mở tài liệu tham khảo",
            value=False,
        )

        st.divider()
        st.subheader("Trạng thái hệ thống")

        task9_ready = _module_available(TASK9_MODULE)
        task10_ready = _module_available(TASK10_MODULE)

        st.markdown(
            f"""
            <div class="status-card">
              <div>{'✅' if task9_ready else '❌'} Task 9 Retrieval</div>
              <div>{'✅' if task10_ready else '❌'} Task 10 Generation</div>
              <div>{'✅' if os.getenv('OPENROUTER_API_KEY') else '⚠️'} OpenRouter API key</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not os.getenv("OPENROUTER_API_KEY"):
            st.caption(
                "Nếu Task 10 dùng OpenRouter, hãy cấu hình "
                "`OPENROUTER_API_KEY` trong `.env`."
            )

        st.divider()

        if st.button(
            "🗑️ Xóa lịch sử trò chuyện",
            use_container_width=True,
        ):
            st.session_state.messages = []
            st.session_state.last_error = None
            st.rerun()

        st.caption(
            "Câu trả lời được tạo từ tài liệu của nhóm. "
            "Hãy kiểm tra nguồn trước khi sử dụng."
        )

    return top_k, show_sources


def _render_suggestions() -> str | None:
    st.subheader("💡 Câu hỏi gợi ý")

    selected: str | None = None

    for row_start in range(0, len(SUGGESTED_QUESTIONS), 2):
        columns = st.columns(2)

        for column_offset, column in enumerate(columns):
            question_index = row_start + column_offset
            if question_index >= len(SUGGESTED_QUESTIONS):
                continue

            question = SUGGESTED_QUESTIONS[question_index]

            if column.button(
                question,
                key=f"suggestion_{question_index}",
                use_container_width=True,
            ):
                selected = question

    return selected


def main() -> None:
    _configure_page()
    _init_state()

    top_k, show_sources = _render_sidebar()

    st.title(f"{APP_ICON} {APP_TITLE}")
    st.markdown(
        """
        <div class="app-subtitle">
        Hỏi đáp dựa trên tài liệu về lịch trình, địa điểm, ẩm thực,
        văn hóa và kinh nghiệm du lịch.
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected_suggestion = _render_suggestions()

    st.divider()

    for message in st.session_state.messages:
        _render_message(message)

    prompt = st.chat_input(
        "Nhập câu hỏi du lịch của bạn...",
        max_chars=1000,
    )

    query = (prompt or selected_suggestion or "").strip()

    if not query:
        return

    # Tránh xử lý lại cùng một suggestion khi Streamlit rerun.
    if (
        st.session_state.messages
        and st.session_state.messages[-1].get("role") == "user"
        and st.session_state.messages[-1].get("content") == query
    ):
        return

    user_message = {
        "role": "user",
        "content": query,
        "sources": [],
        "latency_seconds": None,
    }
    st.session_state.messages.append(user_message)

    with st.chat_message("user", avatar="🧑"):
        st.markdown(query)

    with st.chat_message("assistant", avatar=APP_ICON):
        started_at = time.perf_counter()

        try:
            with st.status(
                "Đang truy xuất tài liệu và tạo câu trả lời...",
                expanded=False,
            ) as status:
                result = run_rag(query, top_k)

                status.update(
                    label=(
                        "Đã hoàn thành "
                        f"({result['task9_function']} → "
                        f"{result['task10_function']})"
                    ),
                    state="complete",
                )

            elapsed = time.perf_counter() - started_at
            answer = result["answer"]
            contexts = result["contexts"]

            st.markdown(answer)
            st.caption(f"Thời gian xử lý: {elapsed:.2f} giây")

            if contexts:
                with st.expander(
                    f"📚 Tài liệu tham khảo ({len(contexts)})",
                    expanded=show_sources,
                ):
                    _render_sources(
                        contexts,
                        expanded=False,
                    )

            assistant_message = {
                "role": "assistant",
                "content": answer,
                "sources": contexts,
                "latency_seconds": elapsed,
                "debug": {
                    "retrieval": result["retrieval_metadata"],
                    "generation": result["generation_metadata"],
                    "task9_function": result["task9_function"],
                    "task10_function": result["task10_function"],
                },
            }
            st.session_state.messages.append(
                assistant_message
            )
            st.session_state.last_error = None

        except Exception as exc:
            elapsed = time.perf_counter() - started_at
            error_message = (
                "Không thể hoàn thành câu hỏi lúc này. "
                f"Chi tiết kỹ thuật: `{type(exc).__name__}: {exc}`"
            )

            st.error(error_message)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": error_message,
                    "sources": [],
                    "latency_seconds": elapsed,
                }
            )
            st.session_state.last_error = str(exc)


if __name__ == "__main__":
    main()