from pathlib import Path
import statistics
import traceback

from src.config import (
    RAW_DIR,
    AUDIO_DIR,
    PROCESSED_DIR,
    VIDEO_METADATA_FILE,
    YOLO_BATCH_SIZE,
    YOLO_CONFIDENCE,
    YOLO_IMAGE_SIZE,
    WHISPER_CHUNK_SECONDS,
    WHISPER_MODEL_PATH,
    YOLO_MODEL_PATH,
)
from src.io_utils import load_json, save_json
from src.probe import probe_video
from src.decompose import extract_frames, extract_audio
from src.vision import load_detector, analyze_frames
from src.speech import transcribe_audio, get_model
from src.events import build_events
from src.semantics import extract_audio_features, detect_scene_changes


VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv", ".avi", ".mov"}
DETECTION_CHECKPOINT_SIZE = 32


def median_frame_interval(frames):
    times = sorted(float(frame["time"]) for frame in frames)

    if len(times) < 2:
        return 1.0

    intervals = [
        times[i] - times[i - 1]
        for i in range(1, len(times))
        if times[i] > times[i - 1]
    ]

    return statistics.median(intervals) if intervals else 1.0


def save_result(output_path, result):
    save_json(output_path, result)


def process_video(video_path, metadata_by_id, detector=None):
    video_id = video_path.stem
    output_path = PROCESSED_DIR / f"{video_id}.json"

    if output_path.exists():
        result = load_json(output_path, default={})
        if not isinstance(result, dict):
            result = {}
    else:
        result = {}

    result.setdefault("id", video_id)
    result.setdefault("source_metadata", metadata_by_id.get(video_id, {}))
    result.setdefault("technical_metadata", {})
    result.setdefault("frames", [])
    result.setdefault("detections", [])
    result.setdefault("audio_file", None)
    result.setdefault(
        "transcript",
        {"language": None, "text": "", "segments": []},
    )
    result.setdefault("audio_features", [])
    result.setdefault("scene_changes", [])
    result.setdefault("events", [])
    result.setdefault("stages", {})
    result.setdefault("errors", [])

    stages = result["stages"]
    result["status"] = "processing"
    result.pop("error", None)
    save_result(output_path, result)

    print(f"\n[VIDEO] {video_path.name}")

    # 1. Технические метаданные
    if not stages.get("probe"):
        try:
            result["technical_metadata"] = probe_video(video_path)
            stages["probe"] = True
            save_result(output_path, result)
            print("[PROBE] Метаданные получены")
        except Exception as exc:
            result["errors"].append({
                "stage": "probe",
                "error": str(exc),
            })
            print(f"[PROBE ERROR] {exc}")

    # 2. Извлечение кадров
    if not stages.get("frames"):
        try:
            result["frames"] = extract_frames(video_path, video_id)
            stages["frames"] = True
            save_result(output_path, result)
            print(f"[FRAMES] Извлечено: {len(result['frames'])}")
        except Exception as exc:
            result["errors"].append({
                "stage": "frames",
                "error": str(exc),
            })
            print(f"[FRAMES ERROR] {exc}")

    frames = result.get("frames", [])

    # 3. Детекция объектов YOLO с промежуточным сохранением
    if frames and not stages.get("detections"):
        try:
            if detector is None:
                detector = load_detector()

            detections = result.get("detections", [])

            # Продолжаем с первого ещё не обработанного кадра.
            if len(detections) > len(frames):
                detections = detections[:len(frames)]
                result["detections"] = detections

            for start in range(len(detections), len(frames),
                               DETECTION_CHECKPOINT_SIZE):
                batch = frames[start:start + DETECTION_CHECKPOINT_SIZE]

                batch_results = analyze_frames(
                    batch,
                    detector,
                    batch_size=YOLO_BATCH_SIZE,
                )

                detections.extend(batch_results)
                result["detections"] = detections
                save_result(output_path, result)

                print(
                    f"[YOLO] {len(detections)}/{len(frames)} кадров"
                )

            stages["detections"] = len(detections) == len(frames)
            save_result(output_path, result)

        except Exception as exc:
            result["errors"].append({
                "stage": "detections",
                "error": str(exc),
            })
            print(f"[YOLO ERROR] {exc}")

    # 4. Извлечение аудио
    audio_path = None

    existing_audio = result.get("audio_file")
    if existing_audio and Path(existing_audio).exists():
        audio_path = Path(existing_audio)
    else:
        expected_audio = AUDIO_DIR / f"{video_id}.wav"
        if expected_audio.exists():
            audio_path = expected_audio

    if audio_path is None:
        try:
            audio_path = extract_audio(video_path, video_id)
            if audio_path:
                audio_path = Path(audio_path)
                result["audio_file"] = str(audio_path)
                stages["audio"] = True
                save_result(output_path, result)
                print(f"[AUDIO] Извлечено: {audio_path.name}")
        except Exception as exc:
            result["errors"].append({
                "stage": "audio",
                "error": str(exc),
            })
            stages["audio"] = False
            print(f"[AUDIO ERROR] {exc}")
    else:
        result["audio_file"] = str(audio_path)
        stages["audio"] = True

    # 5. Аудиопризнаки и транскрипция
    if audio_path and audio_path.exists():
        if not stages.get("audio_features"):
            try:
                result["audio_features"] = extract_audio_features(audio_path)
                stages["audio_features"] = True
                save_result(output_path, result)
                print(
                    f"[AUDIO FEATURES] Окон: "
                    f"{len(result['audio_features'])}"
                )
            except Exception as exc:
                result["errors"].append({
                    "stage": "audio_features",
                    "error": str(exc),
                })
                print(f"[AUDIO FEATURES ERROR] {exc}")

        if not stages.get("speech"):
            try:
                result["transcript"] = transcribe_audio(
                    audio_path,
                    video_id,
                )
                stages["speech"] = True
                save_result(output_path, result)
                print(
                    f"[WHISPER] Сегментов: "
                    f"{len(result['transcript'].get('segments', []))}"
                )
            except Exception as exc:
                result["errors"].append({
                    "stage": "speech",
                    "error": str(exc),
                })
                print(f"[WHISPER ERROR] {exc}")
    else:
        # Отсутствие аудио — допустимый результат, а не бесконечная ошибка.
        stages["audio"] = True
        stages["audio_features"] = True
        stages["speech"] = True
        result["audio_features"] = []
        result["transcript"] = {
            "language": None,
            "text": "",
            "segments": [],
        }
        save_result(output_path, result)
        print("[AUDIO] Аудиодорожка отсутствует")

    # 6. Обнаружение вероятных смен сцен
    if frames and not stages.get("scene_changes"):
        try:
            result["scene_changes"] = detect_scene_changes(frames)
            stages["scene_changes"] = True
            save_result(output_path, result)
            print(
                f"[SCENES] Вероятных смен сцен: "
                f"{len(result['scene_changes'])}"
            )
        except Exception as exc:
            result["errors"].append({
                "stage": "scene_changes",
                "error": str(exc),
            })
            print(f"[SCENES ERROR] {exc}")

    # 7. Формирование временных событий
    if stages.get("detections") and stages.get("speech"):
        try:
            interval = median_frame_interval(frames)
            max_gap = max(2.0, interval * 1.5)

            events = build_events(
                result["detections"],
                result["transcript"],
                max_gap=max_gap,
            )

            # События смены сцен добавляются отдельно.
            for scene in result.get("scene_changes", []):
                events.append({
                    "type": "scene_change",
                    "start": scene["time"],
                    "end": scene["time"],
                    "label": "Вероятная смена сцены",
                    "details": {
                        "score": scene["score"],
                        "method": scene["method"],
                    },
                })

            result["events"] = sorted(
                events,
                key=lambda event: float(event.get("start", 0)),
            )
            stages["events"] = True
            save_result(output_path, result)
            print(f"[EVENTS] Сформировано: {len(result['events'])}")
        except Exception as exc:
            result["errors"].append({
                "stage": "events",
                "error": str(exc),
            })
            print(f"[EVENTS ERROR] {exc}")

    # 8. Проверка качества результатов
    detections = result.get("detections", [])
    detected_objects = sum(
        len(item.get("objects", []))
        for item in detections
    )

    transcript = result.get("transcript", {})
    transcript_text = transcript.get("text", "").strip()

    result["quality_checks"] = {
        "frames_count": len(frames),
        "detections_count": len(detections),
        "detected_objects_count": detected_objects,
        "transcript_empty": len(transcript_text) < 10,
        "transcript_segments_count": len(
            transcript.get("segments", [])
        ),
        "scene_changes_count": len(result.get("scene_changes", [])),
        "events_count": len(result.get("events", [])),
        "frame_interval_seconds": round(
            median_frame_interval(frames), 3
        ) if frames else None,
        "errors_count": len(result["errors"]),
    }

    result["analysis_config"] = {
        "version": "2.0",
        "target_frames_per_video": 400,
        "yolo_model": YOLO_MODEL_PATH.name,
        "yolo_confidence": YOLO_CONFIDENCE,
        "yolo_image_size": YOLO_IMAGE_SIZE,
        "yolo_batch_size": YOLO_BATCH_SIZE,
        "whisper_model": WHISPER_MODEL_PATH.name,
        "whisper_chunk_seconds": WHISPER_CHUNK_SECONDS,
        "scene_change_method": "HSV histogram Bhattacharyya distance",
        "scene_change_threshold": 0.45,
        "audio_feature": "RMS and dBFS per 1-second window",
    }

    required_stages = [
        "probe",
        "frames",
        "detections",
        "audio",
        "audio_features",
        "speech",
        "scene_changes",
        "events",
    ]

    incomplete = [
        stage for stage in required_stages
        if not stages.get(stage, False)
    ]

    if not incomplete:
        result["status"] = (
            "completed_with_warnings"
            if result["errors"]
            else "completed"
        )
    else:
        result["status"] = "partial"
        result["incomplete_stages"] = incomplete

    save_result(output_path, result)

    print(f"[STATUS] {result['status']}")
    print(f"[QUALITY] {result['quality_checks']}")
    print(f"[SAVE] {output_path}")

    return result, detector


def process_all():
    metadata = load_json(VIDEO_METADATA_FILE, default=[])
    metadata_by_id = {
        str(item.get("id")): item
        for item in metadata
    }

    video_files = sorted(
        path for path in RAW_DIR.iterdir()
        if path.is_file()
        and path.suffix.lower() in VIDEO_EXTENSIONS
    )

    if not video_files:
        print(f"В {RAW_DIR} нет видеофайлов.")
        return

    print(f"[START] Видео для обработки: {len(video_files)}")

    print("[MODELS] Подготовка моделей YOLO и Whisper...")
    detector = load_detector()
    get_model()

    results = []

    for video_path in video_files:
        try:
            result, detector = process_video(
                video_path,
                metadata_by_id,
                detector,
            )
            results.append(result)
        except KeyboardInterrupt:
            print("\n[STOP] Обработка прервана пользователем.")
            raise
        except Exception:
            print(f"[FATAL] Ошибка при обработке {video_path.name}")
            traceback.print_exc()

    completed = sum(
        result.get("status") in ("completed", "completed_with_warnings")
        for result in results
    )
    partial = sum(
        result.get("status") == "partial"
        for result in results
    )

    print("\n[SUMMARY]")
    print(f"Обработано: {len(results)}")
    print(f"Завершено: {completed}")
    print(f"Частично: {partial}")
    print(f"Результаты: {PROCESSED_DIR}")


if __name__ == "__main__":
    process_all()
