from pathlib import Path

import yt_dlp

from src.config import RAW_DIR, PROCESSED_DIR, VIDEO_METADATA_FILE
from src.io_utils import load_json, save_json
from src.collect import extract_metadata
from src.pipeline import process_video
from src.speech import get_model
from src.vision import load_detector
from src.topics import run_clustering


VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv", ".avi", ".mov"}

_detector = None


def report(progress, value, description):
    if progress is not None:
        progress(value, desc=description)


def find_video_file(video_id):
    files = [
        path for path in RAW_DIR.glob(f"{video_id}.*")
        if path.suffix.lower() in VIDEO_EXTENSIONS
    ]
    return files[0] if files else None


def add_video_to_catalog(url, discipline, progress=None):
    global _detector

    url = (url or "").strip()
    discipline = (discipline or "").strip()

    if not url:
        raise ValueError("Укажите ссылку на видео.")

    if not discipline:
        raise ValueError("Выберите спортивную дисциплину.")

    report(progress, 0.05, "Получение метаданных...")

    metadata = extract_metadata(url, discipline)
    video_id = str(metadata.get("id") or "")

    if not video_id:
        raise RuntimeError("Не удалось получить ID видео.")

    processed_path = PROCESSED_DIR / f"{video_id}.json"

    if processed_path.exists():
        existing = load_json(processed_path, default={})
        if existing.get("status") in (
            "completed", "completed_with_warnings"
        ):
            return (
                f"Видео «{metadata.get('title', video_id)}» уже "
                "обработано и присутствует в каталоге.",
                video_id,
            )

    report(progress, 0.15, "Проверка исходного видео...")

    video_path = find_video_file(video_id)

    if video_path is None:
        report(progress, 0.20, "Загрузка видео...")

        options = {
            "outtmpl": str(RAW_DIR / "%(id)s.%(ext)s"),
            "format": "bestvideo*+bestaudio/best",
            "merge_output_format": "mp4",
            "noplaylist": True,
            "continuedl": True,
            "retries": 3,
            "fragment_retries": 3,
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            result = ydl.download([metadata["url"]])

        video_path = find_video_file(video_id)

        if video_path is None:
            raise RuntimeError(
                f"Видео не найдено после загрузки. Код yt-dlp: {result}"
            )

    report(progress, 0.35, "Сохранение метаданных...")

    all_metadata = load_json(VIDEO_METADATA_FILE, default=[])
    all_metadata = [
        item for item in all_metadata
        if str(item.get("id")) != video_id
    ]
    all_metadata.append(metadata)
    save_json(VIDEO_METADATA_FILE, all_metadata)

    report(progress, 0.40, "Подготовка моделей YOLO и Whisper...")

    if _detector is None:
        _detector = load_detector()

    get_model()

    report(progress, 0.45, "Запуск анализа видео...")

    result, _detector = process_video(
        video_path,
        {video_id: metadata},
        _detector,
    )

    if result.get("status") not in (
        "completed", "completed_with_warnings"
    ):
        raise RuntimeError(
            "Обработка завершилась не полностью. "
            f"Статус: {result.get('status')}. "
            f"Ошибки: {result.get('errors', [])}"
        )

    report(progress, 0.90, "Обновление тематической кластеризации...")

    clustering_message = ""
    try:
        run_clustering(
            input_dir=PROCESSED_DIR,
            output_path=PROCESSED_DIR / "topic_clusters.json",
            n_clusters=3,
        )
        clustering_message = " Тематическая кластеризация обновлена."
    except Exception as exc:
        clustering_message = (
            f" Кластеризация не обновлена: {exc}"
        )

    report(progress, 1.0, "Видео успешно добавлено.")

    return (
        f"Видео «{metadata.get('title', video_id)}» успешно "
        f"проанализировано и добавлено в каталог."
        f"{clustering_message}",
        video_id,
    )
