"""Task 2 - Crawl bai viet cho Tro ly Huong dan vien Du lich Thong minh.

Moi bai duoc luu thanh JSON gom URL, tieu de, thoi diem crawl va noi dung
Markdown. Script dung requests + BeautifulSoup, nhe hon trinh duyet headless va
phu hop voi cac trang noi dung cong khai duoc render san o phia may chu.
"""

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

# Cac trang chinh thuc bao phu lich trinh, diem den, am thuc va kinh nghiem.
ARTICLE_URLS = [
    "https://vietnam.travel/things-to-do/perfect-weekend-ha-noi",
    "https://vietnam.travel/places-to-go/northern-vietnam/ha-giang",
    "https://vietnam.travel/node/1843",
    "https://vietnam.travel/things-to-do/8-things-to-do-in-dalat",
    "https://vietnam.travel/things-to-do/vietnam-foodie-guide-region",
    "https://vietnam.travel/things-to-do/beginners-guide-vietnamese-street-food",
    "https://www.momo.vn/blog/mon-ngon-quy-nhon-c101dt253",
]


def setup_directory() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _slugify(value: str) -> str:
    value = value.replace("Đ", "D").replace("đ", "d")
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")[:80] or "article"


def _extract_markdown(soup: BeautifulSoup) -> str:
    """Lay noi dung chinh va doi cac khoi van ban pho bien sang Markdown."""
    for unwanted in soup.select("script, style, nav, footer, header, form, aside, noscript"):
        unwanted.decompose()

    root = soup.select_one("article") or soup.select_one("main") or soup.body
    if root is None:
        return ""

    blocks = []
    for element in root.find_all(["h1", "h2", "h3", "p", "li"]):
        text = " ".join(element.get_text(" ", strip=True).split())
        if not text or len(text) < 2:
            continue
        if element.name.startswith("h"):
            level = int(element.name[1])
            blocks.append(f"{'#' * level} {text}")
        elif element.name == "li":
            blocks.append(f"- {text}")
        else:
            blocks.append(text)
    return "\n\n".join(dict.fromkeys(blocks))


def crawl_article(url: str, timeout: int = 60) -> dict:
    """Crawl mot bai viet va tra ve schema metadata thong nhat."""
    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; TravelRAG-Lab/1.0)",
            "Accept-Language": "vi,en;q=0.8",
        },
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    soup = BeautifulSoup(response.text, "html.parser")

    title_node = soup.select_one("meta[property='og:title']")
    title = title_node.get("content", "").strip() if title_node else ""
    if not title and soup.title:
        title = soup.title.get_text(" ", strip=True)
    content = _extract_markdown(soup)
    if len(content) < 500:
        raise ValueError(f"Noi dung crawl qua ngan ({len(content)} ky tu): {url}")

    return {
        "url": url,
        "title": title or "Unknown",
        "date_crawled": datetime.now(timezone.utc).isoformat(),
        "content_markdown": content,
    }


def crawl_all() -> list[Path]:
    """Crawl tat ca URL va luu tung bai thanh mot tep JSON UTF-8."""
    setup_directory()
    saved_files = []
    for index, url in enumerate(ARTICLE_URLS, 1):
        print(f"[{index}/{len(ARTICLE_URLS)}] Crawling: {url}")
        article = crawl_article(url)
        filename = f"article_{index:02d}_{_slugify(article['title'])}.json"
        filepath = DATA_DIR / filename
        filepath.write_text(
            json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        saved_files.append(filepath)
        print(f"  Da luu: {filepath}")
    return saved_files


if __name__ == "__main__":
    files = crawl_all()
    print(f"Hoan tat Task 2: {len(files)} bai viet tai {DATA_DIR}")
