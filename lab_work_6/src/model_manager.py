from src.config import YOLO_MODEL_PATH, WHISPER_MODEL_PATH, DEVICE

_YOLO_MODEL = None
_WHISPER_MODEL = None


def load_yolo():
    """Загружает YOLO11n, автоматически скачивая веса при необходимости."""
    global _YOLO_MODEL

    if _YOLO_MODEL is None:
        from ultralytics import YOLO

        YOLO_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

        if YOLO_MODEL_PATH.exists():
            print(f"[MODEL] Используется YOLO: {YOLO_MODEL_PATH}")
        else:
            print("[MODEL] Веса YOLO11n отсутствуют. Начинается загрузка...")

        _YOLO_MODEL = YOLO(str(YOLO_MODEL_PATH))

        if not YOLO_MODEL_PATH.exists():
            raise RuntimeError(
                f"YOLO не сохранила веса по ожидаемому пути: "
                f"{YOLO_MODEL_PATH}"
            )

        print("[MODEL] YOLO11n готова к работе.")

    return _YOLO_MODEL


def load_whisper():
    """Загружает Whisper Base, скачивая веса при необходимости."""
    global _WHISPER_MODEL

    if _WHISPER_MODEL is None:
        import whisper

        WHISPER_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

        if WHISPER_MODEL_PATH.exists():
            print(f"[MODEL] Используется Whisper: {WHISPER_MODEL_PATH}")
        else:
            print("[MODEL] Веса Whisper Base отсутствуют. Начинается загрузка...")

        _WHISPER_MODEL = whisper.load_model(
            "base",
            download_root=str(WHISPER_MODEL_PATH.parent),
            device=DEVICE,
        )

        if not WHISPER_MODEL_PATH.exists():
            raise RuntimeError(
                f"Whisper не сохранила веса по ожидаемому пути: "
                f"{WHISPER_MODEL_PATH}"
            )

        print("[MODEL] Whisper Base готова к работе.")

    return _WHISPER_MODEL


def ensure_models():
    """Проверяет и подготавливает обе модели."""
    print("[MODELS] Проверка необходимых моделей...")

    load_yolo()
    load_whisper()

    print("[MODELS] Все модели готовы к работе.")
