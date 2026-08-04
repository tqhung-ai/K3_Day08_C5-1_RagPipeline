"""
run_benchmark.py

Role:
- Đọc golden_dataset.json
- Gửi từng câu hỏi tới API RAG
- Thu thập answer và retrieved contexts
- Chuyển dữ liệu sang định dạng RAGAS
- Chạy benchmark
- Lưu kết quả
"""

from pathlib import Path
import json

# ==========================
# Cấu hình
# ==========================

BASE_DIR = Path(__file__).parent

DATASET_PATH = BASE_DIR / "golden_dataset.json"
RESULT_PATH = BASE_DIR / "benchmark_results.json"

# TODO:
# Sau khi backend hoàn thành
# API_URL = "http://localhost:8000/ask"

# ==========================
# Đọc dataset
# ==========================

def load_dataset():
    """Đọc bộ câu hỏi benchmark."""
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ==========================
# Gọi API RAG
# ==========================

def query_rag(question):
    """
    TODO

    Gửi câu hỏi tới API RAG.

    Input:
        question (str)

    Output:
        {
            "answer": "...",
            "contexts": [...],
            "sources": [...]
        }
    """
    pass


# ==========================
# Chuẩn bị dữ liệu cho RAGAS
# ==========================

def build_evaluation_dataset(dataset):
    """
    TODO

    Chuyển dữ liệu sang format EvaluationDataset
    hoặc Dataset của RAGAS.
    """
    pass


# ==========================
# Chạy benchmark
# ==========================

def evaluate_dataset(eval_dataset):
    """
    TODO

    Gọi evaluate(...) của RAGAS
    và lấy kết quả.
    """
    pass


# ==========================
# Lưu kết quả
# ==========================

def save_results(results):
    """Lưu kết quả benchmark."""

    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)


# ==========================
# Main
# ==========================

def main():

    print("Loading golden dataset...")
    dataset = load_dataset()

    print(f"Loaded {len(dataset)} questions.")

    # TODO:
    # 1. Gọi API RAG
    # 2. Thu answer + contexts
    # 3. Build EvaluationDataset
    # 4. Evaluate bằng RAGAS
    # 5. Save kết quả

    print("Benchmark skeleton is ready.")


if __name__ == "__main__":
    main()