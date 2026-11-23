from pathlib import Path
import subprocess
import cv2
import math

from src.config import (
    TARGET_FRAMES_PER_VIDEO,
    MIN_FRAME_INTERVAL_SECONDS,
    FRAMES_DIR,
    AUDIO_DIR,
)


def extract_frames(video_path: Path, video_id: str):
    output_dir = FRAMES_DIR / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Не удалось открыть видео: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if not fps or fps <= 0 or frame_count <= 0:
        cap.release()
        raise RuntimeError("Не удалось определить параметры видео")

    duration = frame_count / fps
    interval = max(
        MIN_FRAME_INTERVAL_SECONDS,
        duration / TARGET_FRAMES_PER_VIDEO
    )

    timestamps = []
    current = 0.0

    while current < duration:
        timestamps.append(current)
        current += interval

    saved = []

    try:
        for index, timestamp in enumerate(timestamps):
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            ok, frame = cap.read()

            if not ok:
                continue

            actual_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            frame_path = output_dir / f"frame_{index:05d}.jpg"

            if cv2.imwrite(str(frame_path), frame):
                saved.append({
                    "time": round(actual_time, 3),
                    "path": str(frame_path),
                })
    finally:
        cap.release()

    print(
        f"[FRAMES] {len(saved)} кадров, "
        f"интервал около {interval:.2f} сек."
    )

    return saved


def extract_audio(video_path: Path, video_id: str):
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    audio_path = AUDIO_DIR / f"{video_id}.wav"

    command = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(audio_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        if audio_path.exists():
            audio_path.unlink()
        raise RuntimeError(
            "Ошибка извлечения аудио: " + result.stderr[-1500:]
        )

    return audio_path
