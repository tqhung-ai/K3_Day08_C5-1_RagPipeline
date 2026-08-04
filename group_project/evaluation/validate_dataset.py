import json
from collections import Counter
from pathlib import Path
from typing import Any


# File golden_dataset.json nằm cùng thư mục với file Python này
BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "golden_dataset.json"

EXPECTED_TOTAL = 20

REQUIRED_FIELDS = {
    "id",
    "question",
    "reference_answer",
    "reference_contexts",
    "category",
    "difficulty",
    "source",
}

ALLOWED_CATEGORIES = {
    "definition",
    "retrieval",
    "multi_context",
    "comparison",
    "reasoning",
    "unanswerable",
}

ALLOWED_DIFFICULTIES = {
    "easy",
    "medium",
    "hard",
}


def load_dataset(file_path: Path) -> list[dict[str, Any]]:
    """Đọc dữ liệu từ file golden_dataset.json."""

    if not file_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy file: {file_path}\n"
            "Hãy đặt golden_dataset.json cùng thư mục với validate_dataset.py."
        )

    try:
        with file_path.open("r", encoding="utf-8") as file:
            dataset = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(
            "File golden_dataset.json không đúng cú pháp JSON.\n"
            f"Lỗi tại dòng {error.lineno}, cột {error.colno}: {error.msg}"
        ) from error

    if not isinstance(dataset, list):
        raise TypeError(
            "Dữ liệu ngoài cùng phải là một JSON array, ví dụ: [ {...}, {...} ]"
        )

    return dataset


def validate_non_empty_string(
    value: Any,
    field_name: str,
    sample_id: str,
) -> list[str]:
    """Kiểm tra một trường có phải chuỗi không rỗng hay không."""

    errors = []

    if not isinstance(value, str):
        errors.append(
            f"{sample_id}: '{field_name}' phải là chuỗi."
        )
    elif not value.strip():
        errors.append(
            f"{sample_id}: '{field_name}' không được để trống."
        )

    return errors


def validate_sample(
    sample: Any,
    position: int,
    seen_ids: set[str],
) -> list[str]:
    """Kiểm tra một câu hỏi trong golden dataset."""

    errors = []
    sample_name = f"Mẫu số {position}"

    if not isinstance(sample, dict):
        return [f"{sample_name}: dữ liệu phải là một JSON object."]

    sample_id = sample.get("id", sample_name)

    # Kiểm tra trường bắt buộc
    missing_fields = REQUIRED_FIELDS - set(sample.keys())

    if missing_fields:
        errors.append(
            f"{sample_id}: thiếu trường {sorted(missing_fields)}."
        )

    # Không kiểm tra tiếp trường bị thiếu để tránh phát sinh lỗi phụ
    if "id" in sample:
        errors.extend(
            validate_non_empty_string(sample["id"], "id", sample_name)
        )

        if isinstance(sample["id"], str):
            normalized_id = sample["id"].strip()

            if normalized_id in seen_ids:
                errors.append(f"{sample_id}: ID bị trùng.")

            seen_ids.add(normalized_id)

            expected_id = f"Q{position:02d}"

            if normalized_id != expected_id:
                errors.append(
                    f"{sample_id}: ID nên là '{expected_id}' "
                    f"theo đúng thứ tự."
                )

    if "question" in sample:
        errors.extend(
            validate_non_empty_string(
                sample["question"],
                "question",
                str(sample_id),
            )
        )

    if "reference_answer" in sample:
        errors.extend(
            validate_non_empty_string(
                sample["reference_answer"],
                "reference_answer",
                str(sample_id),
            )
        )

    # Kiểm tra reference_contexts
    if "reference_contexts" in sample:
        contexts = sample["reference_contexts"]

        if not isinstance(contexts, list):
            errors.append(
                f"{sample_id}: 'reference_contexts' phải là một list."
            )
        else:
            for context_index, context in enumerate(contexts, start=1):
                if not isinstance(context, str):
                    errors.append(
                        f"{sample_id}: context số {context_index} "
                        "phải là chuỗi."
                    )
                elif not context.strip():
                    errors.append(
                        f"{sample_id}: context số {context_index} "
                        "không được để trống."
                    )

    # Kiểm tra category
    if "category" in sample:
        category = sample["category"]

        if category not in ALLOWED_CATEGORIES:
            errors.append(
                f"{sample_id}: category '{category}' không hợp lệ. "
                f"Giá trị hợp lệ: {sorted(ALLOWED_CATEGORIES)}."
            )

    # Kiểm tra difficulty
    if "difficulty" in sample:
        difficulty = sample["difficulty"]

        if difficulty not in ALLOWED_DIFFICULTIES:
            errors.append(
                f"{sample_id}: difficulty '{difficulty}' không hợp lệ. "
                f"Giá trị hợp lệ: {sorted(ALLOWED_DIFFICULTIES)}."
            )

    # Kiểm tra source
    if "source" in sample:
        source = sample["source"]

        if source is not None and not isinstance(source, str):
            errors.append(
                f"{sample_id}: 'source' phải là chuỗi hoặc null."
            )

    # Quy tắc dành cho câu không có đáp án
    if sample.get("category") == "unanswerable":
        contexts = sample.get("reference_contexts")

        if contexts != []:
            errors.append(
                f"{sample_id}: câu unanswerable nên có "
                "'reference_contexts': []."
            )

        if sample.get("source") is not None:
            errors.append(
                f"{sample_id}: câu unanswerable nên có 'source': null."
            )

    return errors


def print_statistics(dataset: list[dict[str, Any]]) -> None:
    """In thống kê cơ bản của dataset."""

    categories = Counter(
        sample.get("category", "missing")
        for sample in dataset
        if isinstance(sample, dict)
    )

    difficulties = Counter(
        sample.get("difficulty", "missing")
        for sample in dataset
        if isinstance(sample, dict)
    )

    print("\nTHỐNG KÊ DATASET")
    print("-" * 45)
    print(f"Tổng số câu: {len(dataset)}")

    print("\nPhân bố category:")
    for category, count in sorted(categories.items()):
        print(f"  - {category}: {count}")

    print("\nPhân bố difficulty:")
    for difficulty, count in sorted(difficulties.items()):
        print(f"  - {difficulty}: {count}")


def main() -> None:
    print(f"Đang kiểm tra: {DATASET_PATH}")

    try:
        dataset = load_dataset(DATASET_PATH)
    except (FileNotFoundError, ValueError, TypeError) as error:
        print("\nDATASET KHÔNG HỢP LỆ")
        print(error)
        raise SystemExit(1)

    errors = []
    seen_ids: set[str] = set()

    if len(dataset) != EXPECTED_TOTAL:
        errors.append(
            f"Dataset phải có đúng {EXPECTED_TOTAL} câu, "
            f"hiện tại có {len(dataset)} câu."
        )

    for position, sample in enumerate(dataset, start=1):
        errors.extend(
            validate_sample(
                sample=sample,
                position=position,
                seen_ids=seen_ids,
            )
        )

    print_statistics(dataset)

    if errors:
        print("\nDATASET KHÔNG HỢP LỆ")
        print("-" * 45)

        for index, error in enumerate(errors, start=1):
            print(f"{index}. {error}")

        raise SystemExit(1)

    print("\nDATASET HỢP LỆ")
    print("Không phát hiện lỗi cấu trúc trong golden_dataset.json.")


if __name__ == "__main__":
    main()