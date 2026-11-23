from src.config import (
    YOLO_CONFIDENCE,
    YOLO_IMAGE_SIZE,
    DEVICE,
    YOLO_BATCH_SIZE,
)
from src.model_manager import load_yolo


def load_detector():
    return load_yolo()


def analyze_frames(frames, model, batch_size=YOLO_BATCH_SIZE):
    detections = []

    for start in range(0, len(frames), batch_size):
        batch = frames[start:start + batch_size]
        paths = [frame["path"] for frame in batch]

        results = model.predict(
            source=paths,
            conf=YOLO_CONFIDENCE,
            imgsz=YOLO_IMAGE_SIZE,
            device=0 if DEVICE == "cuda" else "cpu",
            batch=batch_size,
            verbose=False,
        )

        for frame, result in zip(batch, results):
            objects = []

            if result.boxes is not None:
                for box in result.boxes:
                    class_id = int(box.cls.item())

                    objects.append({
                        "class_id": class_id,
                        "class_name": model.names[class_id],
                        "confidence": round(float(box.conf.item()), 4),
                        "bbox_xyxy": [
                            round(float(x), 2)
                            for x in box.xyxy[0].tolist()
                        ],
                    })

            detections.append({
                "time": frame["time"],
                "objects": objects,
            })

    return detections
