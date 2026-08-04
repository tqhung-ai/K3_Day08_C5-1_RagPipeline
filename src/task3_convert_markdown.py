"""Task 3 - Chuan hoa cam nang PDF va bai crawl JSON sang Markdown."""

import json
import re
from pathlib import Path

from markitdown import MarkItDown


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"

CAO_BANG_GUIDE = "cam-nang-du-lich-cao-bang.pdf"
CAO_BANG_SECTIONS = {
    "GIỚI THIỆU CHUNG",
    "CỘI NGUỒN CÁCH MẠNG",
    "NON NƯỚC CAO BẰNG",
    "TRẢI NGHIỆM VÙNG CAO",
    "SẮC MÀU MỘT VÙNG ĐÔNG BẮC",
    "HƯƠNG VỊ ĐÔNG BẮC",
    "THÔNG TIN HỮU ÍCH",
}


def _collapse_doubled_glyphs(text: str) -> str:
    """Sua chu bi lap doi do PDF chua hai lop glyph trung nhau."""
    def collapse_token(token: str) -> str:
        runs = [match.group(0) for match in re.finditer(r"(.)\1*", token)]
        if not runs:
            return token
        paired_chars = sum(len(run) for run in runs if len(run) % 2 == 0)
        if paired_chars / len(token) < 0.7:
            return token
        return "".join(
            run[: len(run) // 2] if len(run) % 2 == 0 else run for run in runs
        )

    return "".join(
        part if part.isspace() else collapse_token(part)
        for part in re.split(r"(\s+)", text)
    )


def _extract_cao_bang_guide(filepath: Path) -> str:
    """Trich xuat rieng cam nang Cao Bang va loai cac trang PDF bi lap."""
    import pdfplumber

    extracted_pages = []
    with pdfplumber.open(filepath) as document:
        # Tep goc luu moi trang ruot hai lan voi CropBox trai/phai khac nhau.
        # Trang ban do dau tien co bo cuc do hoa nen duoc thay bang phan tong quan
        # co cau truc o dau Markdown; cac trang noi dung bat dau tu chi so 3.
        page_indexes = range(3, len(document.pages) - 1, 2)
        for page_index in page_indexes:
            text = document.pages[page_index].extract_text(x_tolerance=1, y_tolerance=3)
            if text:
                extracted_pages.append(text)

    return "\n\n".join(extracted_pages)


def _clean_cao_bang_guide(content: str) -> str:
    """Chuan hoa cam nang Cao Bang thanh Markdown de tim kiem RAG."""
    cleaned_lines: list[str] = []
    previous_line = ""

    for raw_line in content.replace("\x0c", "\n").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            if cleaned_lines and cleaned_lines[-1]:
                cleaned_lines.append("")
            continue

        line = _collapse_doubled_glyphs(line)
        line = re.sub(r"^[]+\s*", "- ", line)

        # Dau trang, chan trang va so trang khong mang noi dung tra cuu.
        if "https://caobangtourism.vn Facebook Fanpage:" in line:
            continue
        if re.fullmatch(r"\d{1,2}", line):
            continue
        if line in {"CẨM NANG", "DU LỊCH", "CAO BẰNG"}:
            continue

        header_prefix = "CẨM NANG DU LỊCH CAO BẰNG"
        if line.startswith(header_prefix):
            remainder = line[len(header_prefix) :].strip()
            if not remainder:
                continue
            line = remainder

        if line in CAO_BANG_SECTIONS:
            line = f"## {line.title()}"
        elif (
            line.isupper()
            and 3 <= len(line) <= 100
            and any(character.isalpha() for character in line)
            and not line.startswith(("HOTLINE", "TEL", "MOBILE"))
        ):
            line = f"### {line.title()}"

        # Loai dong trung lien tiep, thuong sinh ra tu lop chu trong anh.
        if line == previous_line:
            continue
        cleaned_lines.append(line)
        previous_line = line

    body = "\n".join(cleaned_lines)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return (
        "# Cẩm nang du lịch Cao Bằng\n\n"
        "**Đơn vị xuất bản:** Sở Văn hóa, Thể thao và Du lịch Cao Bằng\n\n"
        "**Năm xuất bản:** 2025\n\n"
        "**Trang thông tin:** https://caobangtourism.vn\n\n"
        "---\n\n"
        "## Tổng quan\n\n"
        "Cao Bằng là tỉnh miền núi biên giới ở Đông Bắc Việt Nam, có diện tích "
        "6.724,6 km² và hơn 333 km đường biên giới giáp Quảng Tây, Trung Quốc. "
        "Tỉnh nổi bật với địa hình karst, hệ thống sông, hồ, thác nước, hang động, "
        "di tích cách mạng và văn hóa của các dân tộc Tày, Nùng, Mông, Dao, Sán Chỉ, "
        "Lô Lô. Công viên địa chất Non nước Cao Bằng được UNESCO công nhận là Công "
        "viên địa chất toàn cầu năm 2018.\n\n"
        f"{body}\n"
    )


def convert_legal_docs() -> list[Path]:
    """Convert PDF/DOCX trong landing/legal sang Markdown UTF-8."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    if not legal_dir.exists():
        return []

    converter = MarkItDown()
    outputs = []
    for filepath in sorted(legal_dir.iterdir()):
        if filepath.suffix.lower() not in {".pdf", ".docx", ".doc"}:
            continue
        print(f"Converting: {filepath.name}")
        if filepath.name == CAO_BANG_GUIDE:
            content = _clean_cao_bang_guide(_extract_cao_bang_guide(filepath))
        else:
            result = converter.convert(str(filepath))
            content = (result.text_content or "").strip()
        content = content.strip()
        if len(content) < 200:
            raise ValueError(f"Noi dung convert qua ngan: {filepath}")
        output_path = output_dir / f"{filepath.stem}.md"
        output_path.write_text(content + "\n", encoding="utf-8")
        outputs.append(output_path)
        print(f"  Da luu: {output_path}")
    return outputs


def convert_news_articles() -> list[Path]:
    """Chuyen JSON bai viet sang Markdown, kem metadata truy vet nguon."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)
    if not news_dir.exists():
        return []

    outputs = []
    for filepath in sorted(news_dir.glob("*.json")):
        print(f"Converting: {filepath.name}")
        data = json.loads(filepath.read_text(encoding="utf-8"))
        title = str(data.get("title") or "Unknown").strip()
        source = str(data.get("url") or "N/A").strip()
        crawled = str(data.get("date_crawled") or "N/A").strip()
        body = str(data.get("content_markdown") or data.get("content") or "").strip()
        if len(body) < 200:
            raise ValueError(f"Noi dung bai viet qua ngan: {filepath}")

        content = (
            f"# {title}\n\n"
            f"**Source:** {source}\n\n"
            f"**Crawled:** {crawled}\n\n"
            "---\n\n"
            f"{body}\n"
        )
        output_path = output_dir / f"{filepath.stem}.md"
        output_path.write_text(content, encoding="utf-8")
        outputs.append(output_path)
        print(f"  Da luu: {output_path}")
    return outputs


def convert_all() -> list[Path]:
    """Convert toan bo corpus va tra ve danh sach tep da tao."""
    print("Task 3: Convert travel corpus to Markdown")
    outputs = convert_legal_docs() + convert_news_articles()
    print(f"Hoan tat Task 3: {len(outputs)} tep tai {OUTPUT_DIR}")
    return outputs


if __name__ == "__main__":
    convert_all()
