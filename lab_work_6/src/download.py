"""
Загрузка через yt-dlp. Запускайте только для материалов,
которые вы вправе сохранять и анализировать.
"""
from pathlib import Path
import yt_dlp

from src.config import RAW_DIR, VIDEO_METADATA_FILE
from src.io_utils import load_json


def download_all():
    metadata = load_json(VIDEO_METADATA_FILE, default=[])
    if not metadata:
        raise RuntimeError("Сначала выполните: python -m src.collect")

    options = {
        "outtmpl": str(RAW_DIR / "%(id)s.%(ext)s"),
        "format": "bestvideo*+bestaudio/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "continuedl": True,
        "retries": 2,
        "fragment_retries": 2,
        "ignoreerrors": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        for item in metadata:
            video_id = item.get("id")
            if not video_id:
                continue
            existing = list(RAW_DIR.glob(f"{video_id}.*"))
            if existing:
                print(f"[SKIP] Уже загружен: {existing[0].name}")
                continue
            print(f"[DOWNLOAD] {item.get('title')}")
            try:
                ydl.download([item["url"]])
            except Exception as exc:
                print(f"[ERROR] {item['url']}: {exc}")


if __name__ == "__main__":
    download_all()
