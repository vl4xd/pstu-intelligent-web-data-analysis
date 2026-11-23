from pathlib import Path
import torch

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
METADATA_DIR = DATA_DIR / "metadata"

FRAMES_DIR = DATA_DIR / "frames_v2"
AUDIO_DIR = DATA_DIR / "audio_v2"
PROCESSED_DIR = DATA_DIR / "processed_v2"

URLS_FILE = METADATA_DIR / "video_urls.txt"
VIDEO_METADATA_FILE = METADATA_DIR / "videos.json"

YOLO_MODEL_PATH = ROOT / "models" / "yolo" / "yolo11n.pt"
WHISPER_MODEL_PATH = ROOT / "models" / "whisper" / "base.pt"

TARGET_FRAMES_PER_VIDEO = 400
MIN_FRAME_INTERVAL_SECONDS = 1.0
MAX_VIDEO_SECONDS = None

YOLO_CONFIDENCE = 0.35
YOLO_IMAGE_SIZE = 640
YOLO_BATCH_SIZE = 16

WHISPER_LANGUAGE = None
WHISPER_CHUNK_SECONDS = 600

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

for directory in (
    RAW_DIR, METADATA_DIR, FRAMES_DIR, AUDIO_DIR, PROCESSED_DIR
):
    directory.mkdir(parents=True, exist_ok=True)
