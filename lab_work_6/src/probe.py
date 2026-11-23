import json
import subprocess
from pathlib import Path


def probe_video(video_path: Path) -> dict:
    command = [
        "ffprobe", "-v", "error",
        "-show_streams", "-show_format",
        "-of", "json", str(video_path)
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)

    video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    if not video_streams:
        raise ValueError(f"В файле нет видеопотока: {video_path}")

    v = video_streams[0]
    fmt = data.get("format", {})
    return {
        "file": video_path.name,
        "container": fmt.get("format_name"),
        "duration_seconds": float(fmt["duration"]) if fmt.get("duration") else None,
        "size_bytes": int(fmt["size"]) if fmt.get("size") else video_path.stat().st_size,
        "video_codec": v.get("codec_name"),
        "width": v.get("width"),
        "height": v.get("height"),
        "fps": v.get("avg_frame_rate"),
        "video_bitrate": v.get("bit_rate"),
        "has_audio": bool(audio_streams),
        "audio_codec": audio_streams[0].get("codec_name") if audio_streams else None,
    }
