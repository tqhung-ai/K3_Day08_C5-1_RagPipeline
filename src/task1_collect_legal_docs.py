"""Task 1 - Thu thap cam nang du lich dang PDF tu nguon chinh thuc.

De tai nhom: Tro ly Huong dan vien Du lich Thong minh.
Du lieu duoc luu trong ``data/landing/legal`` de tuong thich voi cau truc va
bo test cua bai lab. Trong de tai nay, thu muc ``legal`` chua cac cam nang PDF
chinh thong thay vi van ban chinh sach dai hoc.
"""

from pathlib import Path

import requests


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

# Nguon cong khai: cam nang dia phuong va tai lieu tu co so giao duc Viet Nam.
GUIDE_SOURCES = [
    {
        "url": "https://cdnc.heyzine.com/files/uploaded/v3/00f6ad28eaa8972b59418db41a47e43c6593ceda.pdf",
        "filename": "cam-nang-du-lich-cao-bang.pdf",
        "description": "Cam nang du lich Cao Bang bang tieng Viet",
    },
    {
        "url": "https://inest.hust.edu.vn/documents/172165/172188/dulich-quangbinh.pdf/89bf8145-8ad4-4964-bed4-972278cb23a4",
        "filename": "cam-nang-du-lich-quang-binh.pdf",
        "description": "Cam nang du lich Quang Binh bang tieng Viet",
    },
    {
        "url": "https://cdnc.heyzine.com/files/uploaded/80476d8f1cbdc6ade13c4b5033b193a5364df364.pdf",
        "filename": "cam-nang-du-lich-quang-ninh.pdf",
        "description": "Cam nang du lich Quang Ninh bang tieng Viet",
    },
]


def setup_directory() -> None:
    """Tao thu muc dau ra neu chua ton tai."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def download_file(url: str, filename: str, timeout: int = 60) -> Path:
    """Tai mot PDF, kiem tra chu ky file va ghi an toan vao thu muc landing."""
    destination = DATA_DIR / filename
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "Mozilla/5.0 (compatible; TravelRAG-Lab/1.0)"},
    )
    response.raise_for_status()
    content = response.content
    if len(content) < 1024 or not content.startswith(b"%PDF"):
        raise ValueError(f"Nguon khong tra ve PDF hop le: {url}")

    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.write_bytes(content)
    temporary.replace(destination)
    return destination


def collect_all(overwrite: bool = False) -> list[Path]:
    """Tai toan bo cam nang; bo qua file hop le da co khi chay lai."""
    setup_directory()
    downloaded = []
    for index, source in enumerate(GUIDE_SOURCES, 1):
        destination = DATA_DIR / source["filename"]
        if not overwrite and destination.exists() and destination.stat().st_size > 1024:
            print(f"[{index}/{len(GUIDE_SOURCES)}] Da co: {destination.name}")
        else:
            print(f"[{index}/{len(GUIDE_SOURCES)}] Dang tai: {source['description']}")
            download_file(source["url"], source["filename"])
            print(f"  Da luu: {destination}")
        downloaded.append(destination)
    return downloaded


if __name__ == "__main__":
    files = collect_all()
    print(f"Hoan tat Task 1: {len(files)} cam nang tai {DATA_DIR}")
