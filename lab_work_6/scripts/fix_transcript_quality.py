
import json
from pathlib import Path

ROOT = Path("data/processed_v2")

# Для этих видео проблемы распознавания подтверждены
WARNINGS = {
    "football": "Транскрипт отсутствует: Whisper распознал только музыкальный маркер.",
    "basketball": "Низкое качество транскрипции: много музыкальных меток, шумов и бессвязных фрагментов.",
}

updated = 0

for path in ROOT.glob("*.json"):
    if path.name == "topic_clusters.json":
        continue

    data = json.loads(path.read_text(encoding="utf-8"))
    metadata = data.get("source_metadata", {})
    discipline = metadata.get("discipline")

    transcript = data.get("transcript", {})
    transcript_text = (
        transcript.get("text", "")
        if isinstance(transcript, dict)
        else ""
    ).strip()

    quality = data.setdefault("quality_checks", {})

    # Короткий или состоящий только из музыкального маркера текст
    transcript_empty = (
        len(transcript_text) < 10
        or transcript_text == "🎵"
    )

    quality["transcript_empty"] = transcript_empty
    quality["transcript_chars"] = len(transcript_text)

    if discipline in WARNINGS:
        quality["transcript_quality_warning"] = WARNINGS[discipline]
    else:
        quality.pop("transcript_quality_warning", None)

    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    updated += 1

    print(
        f"{discipline}: "
        f"transcript_empty={transcript_empty}, "
        f"chars={len(transcript_text)}, "
        f"warning={discipline in WARNINGS}"
    )

print(f"\nОбновлено JSON-файлов: {updated}")
