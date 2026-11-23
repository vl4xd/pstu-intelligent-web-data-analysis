import json
import re
from pathlib import Path


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    temp_path.replace(path)


def load_json(path: Path, default=None):
    if not path.exists():
        return [] if default is None else default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def safe_name(value: str) -> str:
    value = re.sub(r"[^\w.-]+", "_", value, flags=re.UNICODE).strip("_.")
    return value[:100] or "video"
