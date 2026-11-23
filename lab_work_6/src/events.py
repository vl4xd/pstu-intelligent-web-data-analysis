from collections import defaultdict


def build_events(detections, transcript, max_gap=30.0):
    events = []

    # Группируем наблюдения объектов по классам.
    observations = defaultdict(list)

    for frame in detections:
        counts = defaultdict(int)

        for obj in frame.get("objects", []):
            name = obj.get("class_name", "unknown")
            counts[name] += 1

        for name, count in counts.items():
            observations[name].append({
                "time": float(frame["time"]),
                "count": count,
            })

    for name, items in observations.items():
        items.sort(key=lambda x: x["time"])

        group = []
        for item in items:
            if group and item["time"] - group[-1]["time"] > max_gap:
                events.append(_visual_event(name, group))
                group = []

            group.append(item)

        if group:
            events.append(_visual_event(name, group))

    # События речи сохраняем с исходными временными метками Whisper.
    for segment in transcript.get("segments", []):
        text = segment.get("text", "").strip()

        if text:
            events.append({
                "type": "speech",
                "start": float(segment["start"]),
                "end": float(segment["end"]),
                "label": "Речь",
                "text": text,
            })

    return sorted(
        events,
        key=lambda item: (item["start"], item["end"])
    )


def _visual_event(name, group):
    return {
        "type": "visual",
        "start": group[0]["time"],
        "end": group[-1]["time"],
        "label": f"Обнаружен объект: {name}",
        "details": {
            "class_name": name,
            "observations": len(group),
            "total_detections": sum(x["count"] for x in group),
        },
    }
