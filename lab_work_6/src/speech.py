import json
import subprocess
from pathlib import Path

from src.model_manager import load_whisper

from src.config import (
    WHISPER_LANGUAGE,
    WHISPER_CHUNK_SECONDS,
    DEVICE,
    AUDIO_DIR,
)

def get_model():
    return load_whisper()


def transcribe_audio(audio_path: Path, video_id: str):
    import wave

    with wave.open(str(audio_path), "rb") as wav:
        duration = wav.getnframes() / wav.getframerate()

    chunk_dir = AUDIO_DIR / "transcripts" / video_id
    chunk_dir.mkdir(parents=True, exist_ok=True)

    chunk_count = max(
        1,
        int((duration + WHISPER_CHUNK_SECONDS - 1)
            // WHISPER_CHUNK_SECONDS)
    )

    model = get_model()
    language = WHISPER_LANGUAGE
    all_segments = []
    all_text = []

    for index in range(chunk_count):
        start = index * WHISPER_CHUNK_SECONDS
        chunk_duration = min(
            WHISPER_CHUNK_SECONDS,
            duration - start
        )

        result_path = chunk_dir / f"chunk_{index:04d}.json"

        if result_path.exists():
            result = json.loads(
                result_path.read_text(encoding="utf-8")
            )
            print(f"[WHISPER] Загружена готовая часть {index + 1}/{chunk_count}")
        else:
            chunk_path = chunk_dir / f"chunk_{index:04d}.wav"

            command = [
                "ffmpeg", "-y",
                "-ss", str(start),
                "-i", str(audio_path),
                "-t", str(chunk_duration),
                "-ac", "1",
                "-ar", "16000",
                "-c:a", "pcm_s16le",
                str(chunk_path),
            ]

            proc = subprocess.run(
                command,
                capture_output=True,
                text=True
            )

            if proc.returncode != 0:
                raise RuntimeError(
                    "Ошибка подготовки аудиофрагмента: "
                    + proc.stderr[-1000:]
                )

            try:
                result = model.transcribe(
                    str(chunk_path),
                    language=language,
                    task="transcribe",
                    fp16=(DEVICE == "cuda"),
                    verbose=False,
                    condition_on_previous_text=False,
                )
            finally:
                if chunk_path.exists():
                    chunk_path.unlink()

            if language is None:
                language = result.get("language")

            result = {
                "language": result.get("language"),
                "text": result.get("text", "").strip(),
                "segments": [
                    {
                        "start": round(
                            float(seg["start"]) + start, 3
                        ),
                        "end": round(
                            float(seg["end"]) + start, 3
                        ),
                        "text": seg["text"].strip(),
                    }
                    for seg in result.get("segments", [])
                ],
            }

            result_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            print(f"[WHISPER] Сохранена часть {index + 1}/{chunk_count}")

        all_text.append(result.get("text", ""))
        all_segments.extend(result.get("segments", []))

    return {
        "language": language,
        "text": " ".join(x for x in all_text if x).strip(),
        "segments": sorted(
            all_segments,
            key=lambda x: x["start"]
        ),
    }
