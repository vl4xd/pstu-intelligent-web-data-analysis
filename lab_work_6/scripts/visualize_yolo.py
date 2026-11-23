
import json
from pathlib import Path
from collections import Counter

from PIL import Image, ImageDraw, ImageFont

ROOT = Path("data/processed_v2")
OUTPUT = Path("reports/yolo_contact_sheet.jpg")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

videos = []

for path in sorted(ROOT.glob("*.json")):
    if path.name == "topic_clusters.json":
        continue

    data = json.loads(path.read_text(encoding="utf-8"))
    frames = data.get("frames", [])
    detections = data.get("detections", [])

    if not frames:
        continue

    metadata = data.get("source_metadata", {})
    discipline = metadata.get("discipline", path.stem)

    # Сводная статистика по всему видео
    classes = Counter(
        obj["class_name"]
        for detection in detections
        for obj in detection.get("objects", [])
    )

    print(f"\n{discipline}:")
    print("Всего кадров:", len(frames))
    print("Кадров с детекциями:", sum(
        bool(x.get("objects")) for x in detections
    ))
    print("Объектов:", sum(classes.values()))
    print("Топ классов:", classes.most_common(8))

    # Выбираем кадры из трёх частей видео
    n = len(frames)
    indices = [
        n // 6,
        n // 2,
        (5 * n) // 6,
    ]

    for index in indices:
        frame = frames[index]
        detection = (
            detections[index]
            if index < len(detections)
            else {"objects": []}
        )

        image_path = Path(frame["path"])
        if not image_path.exists():
            print("Не найден кадр:", image_path)
            continue

        image = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(image)

        scale = min(900 / image.width, 550 / image.height, 1)
        if scale < 1:
            image = image.resize((
                int(image.width * scale),
                int(image.height * scale)
            ))
            draw = ImageDraw.Draw(image)

        for obj in detection.get("objects", []):
            x1, y1, x2, y2 = obj["bbox_xyxy"]
            x1, y1, x2, y2 = [
                int(v * scale) for v in (x1, y1, x2, y2)
            ]

            name = obj["class_name"]
            conf = obj["confidence"]

            draw.rectangle((x1, y1, x2, y2), outline="red", width=3)
            draw.text(
                (x1, max(0, y1 - 18)),
                f"{name} {conf:.2f}",
                fill="yellow",
                stroke_width=2,
                stroke_fill="black"
            )

        timestamp = frame.get("time", 0)

        videos.append((discipline, timestamp, image))

# Собираем изображения в контактный лист
cell_w = 920
cell_h = 610
columns = 2
rows = (len(videos) + columns - 1) // columns

sheet = Image.new(
    "RGB",
    (columns * cell_w, rows * cell_h),
    "white"
)
draw = ImageDraw.Draw(sheet)

for i, (discipline, timestamp, image) in enumerate(videos):
    x = (i % columns) * cell_w
    y = (i // columns) * cell_h

    draw.text(
        (x + 10, y + 5),
        f"{discipline} | {timestamp:.1f} sec",
        fill="black"
    )

    sheet.paste(image, (x + 10, y + 35))

sheet.save(OUTPUT, quality=90)

print("\nКонтактный лист сохранён:", OUTPUT.resolve())
print("Изображений:", len(videos))
