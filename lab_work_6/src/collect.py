from datetime import datetime, timezone
from pathlib import Path
import yt_dlp

from src.config import URLS_FILE, VIDEO_METADATA_FILE
from src.io_utils import load_json, save_json


def read_url_list(path: Path = URLS_FILE):
    items = []
    if not path.exists():
        raise FileNotFoundError(f"Не найден список ссылок: {path}")

    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            discipline, url = line.split("|", 1)
        except ValueError:
            print(f"[WARN] Строка {line_no}: ожидается discipline|URL")
            continue
        items.append({"discipline": discipline.strip(), "url": url.strip()})
    return items


def extract_metadata(url: str, discipline: str):
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": 30,
        "retries": 2,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)

    return {
        "id": str(info.get("id") or ""),
        "title": info.get("title"),
        "url": info.get("webpage_url") or url,
        "platform": info.get("extractor_key"),
        "author": info.get("uploader") or info.get("channel"),
        "discipline": discipline,
        "duration_seconds": info.get("duration"),
        "upload_date": info.get("upload_date"),
        "view_count": info.get("view_count"),
        "description": info.get("description"),
        "tags": info.get("tags") or [],
        "categories": info.get("categories") or [],
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }


def collect_all():
    existing = load_json(VIDEO_METADATA_FILE, default=[])
    by_url = {item.get("url"): item for item in existing if item.get("url")}

    for item in read_url_list():
        url, discipline = item["url"], item["discipline"]
        if url in by_url:
            print(f"[SKIP] Уже есть: {url}")
            continue
        print(f"[META] {discipline}: {url}")
        try:
            metadata = extract_metadata(url, discipline)
            if not metadata["id"]:
                raise ValueError("yt-dlp не вернул идентификатор видео")
            by_url[url] = metadata
            save_json(VIDEO_METADATA_FILE, list(by_url.values()))
            print(f"[OK] {metadata['title']} ({metadata['duration_seconds']} сек.)")
        except Exception as exc:
            print(f"[ERROR] {url}: {exc}")

    result = list(by_url.values())
    save_json(VIDEO_METADATA_FILE, result)
    print(f"\nМетаданные: {len(result)} записей -> {VIDEO_METADATA_FILE}")


if __name__ == "__main__":
    collect_all()
