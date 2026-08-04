"""Task 3 - Chuan hoa cam nang PDF va bai crawl JSON sang Markdown."""

import json
from pathlib import Path

from markitdown import MarkItDown


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


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
        result = converter.convert(str(filepath))
        content = (result.text_content or "").strip()
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
