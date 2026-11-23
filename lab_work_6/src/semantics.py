from pathlib import Path
import math
import wave
from array import array

import cv2


def extract_audio_features(audio_path: Path, window_seconds: float = 1.0):
    """
    Рассчитывает RMS и уровень громкости в dBFS для последовательных
    окон аудиозаписи. Входной WAV должен быть PCM.
    """
    features = []

    with wave.open(str(audio_path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()

        if sample_width != 2:
            raise ValueError(
                f"Ожидался 16-битный PCM WAV, получено: {sample_width * 8} бит"
            )

        samples_per_window = max(1, int(sample_rate * window_seconds))
        frames_per_window = samples_per_window

        total_frames = wav.getnframes()
        position = 0

        while position < total_frames:
            count = min(frames_per_window, total_frames - position)
            raw = wav.readframes(count)

            if not raw:
                break

            samples = array("h")
            samples.frombytes(raw)

            if not samples:
                break

            if channels > 1:
                mono_samples = []
                for i in range(0, len(samples), channels):
                    group = samples[i:i + channels]
                    mono_samples.append(sum(group) / len(group))
                values = mono_samples
            else:
                values = samples

            mean_square = sum(float(x) ** 2 for x in values) / len(values)
            rms = math.sqrt(mean_square) / 32768.0
            dbfs = 20.0 * math.log10(max(rms, 1e-8))

            start = position / sample_rate
            end = min((position + count) / sample_rate, total_frames / sample_rate)

            features.append({
                "start": round(start, 3),
                "end": round(end, 3),
                "rms": round(rms, 6),
                "dbfs": round(dbfs, 2),
            })

            position += count

    return features


def detect_scene_changes(frames, threshold: float = 0.45):
    """
    Ищет вероятные смены сцены по расстоянию Бхаттачарьи
    между цветовыми гистограммами соседних сохранённых кадров.

    Это приближённая оценка: точность временной привязки зависит
    от интервала извлечения кадров.
    """
    ordered_frames = sorted(frames, key=lambda item: item["time"])
    changes = []
    previous_hist = None

    for frame in ordered_frames:
        image_path = Path(frame["path"])
        image = cv2.imread(str(image_path))

        if image is None:
            continue

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist(
            [hsv],
            [0, 1],
            None,
            [32, 32],
            [0, 180, 0, 256],
        )
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)

        if previous_hist is not None:
            distance = float(
                cv2.compareHist(
                    previous_hist,
                    hist,
                    cv2.HISTCMP_BHATTACHARYYA,
                )
            )

            if distance >= threshold:
                changes.append({
                    "time": round(float(frame["time"]), 3),
                    "score": round(distance, 4),
                    "method": "histogram_bhattacharyya",
                })

        previous_hist = hist

    return changes
