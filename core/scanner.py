import os
import re
import subprocess
from pathlib import Path
from typing import Optional
from core.database import Database
from core.models import Asset


STOP_WORDS = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "他", "她", "它", "们"}

ENGLISH_STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "at", "to", "in", "on", "for", "of", "by", "with", "and",
    "or", "not", "this", "that", "it", "its", "as", "but",
    "from", "into", "via", "per",
}

SUPPORTED_EXTENSIONS = {
    "video": {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv"},
    "image": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"},
    "bgm": {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"},
    "voice": {".mp3", ".wav", ".ogg", ".m4a"},
}


def _classify_file(ext: str) -> str:
    ext = ext.lower()
    for asset_type, extensions in SUPPORTED_EXTENSIONS.items():
        if ext in extensions:
            return asset_type
    return ""


def _extract_tags_from_name(filename: str) -> list[str]:
    name = Path(filename).stem
    parts = re.split(r"[-_\s]+", name)
    tags = []
    for p in parts:
        if not p:
            continue
        p_lower = p.lower()
        if len(p) <= 1:
            continue
        if p_lower.isdigit():
            continue
        if p_lower in STOP_WORDS or p_lower in ENGLISH_STOP_WORDS:
            continue
        if re.match(r'^[a-z]{2,}$', p_lower) or re.match(r'^[\u4e00-\u9fff]+$', p):
            tags.append(p)
    return tags


def _get_file_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def _get_video_info(path: str) -> tuple[Optional[float], int, int]:
    import json
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", path],
            capture_output=True, text=True, errors='replace', timeout=30,
        )
        data = json.loads(result.stdout)
        duration: Optional[float] = None
        width, height = 0, 0

        if "format" in data and "duration" in data["format"]:
            duration = float(data["format"]["duration"])

        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                width = stream.get("width", 0)
                height = stream.get("height", 0)
                break

        return duration, width, height
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, KeyError, ValueError, OSError):
        return None, 0, 0


def _get_audio_info(path: str) -> Optional[float]:
    import json
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", path],
            capture_output=True, text=True, errors='replace', timeout=30,
        )

        data = json.loads(result.stdout)
        if "format" in data and "duration" in data["format"]:
            return float(data["format"]["duration"])
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, KeyError, ValueError, OSError):
        return None


class AssetScanner:
    def __init__(self, database: Database, assets_dir: str = "./assets"):
        self.db = database
        self.assets_dir = assets_dir

    def scan_all(self) -> int:
        count = 0
        for asset_type in ["videos", "images", "bgm", "voice"]:
            type_dir = os.path.join(self.assets_dir, asset_type)
            if not os.path.isdir(type_dir):
                continue
            actual_type = asset_type.rstrip("s")
            for root, _dirs, files in os.walk(type_dir):
                for filename in files:
                    ext = Path(filename).suffix.lower()
                    if not _classify_file(ext):
                        continue
                    full_path = os.path.join(root, filename)
                    if self._process_file(full_path, filename, actual_type):
                        count += 1
        return count

    def scan_incremental(self) -> int:
        count = 0
        for asset_type in ["videos", "images", "bgm", "voice"]:
            type_dir = os.path.join(self.assets_dir, asset_type)
            if not os.path.isdir(type_dir):
                continue
            actual_type = asset_type.rstrip("s")
            for root, _dirs, files in os.walk(type_dir):
                for filename in files:
                    ext = Path(filename).suffix.lower()
                    if not _classify_file(ext):
                        continue
                    if self.db.file_exists(filename):
                        continue
                    full_path = os.path.join(root, filename)
                    if self._process_file(full_path, filename, actual_type):
                        count += 1
        return count

    def remove_deleted(self) -> int:
        deleted = 0
        for asset in self.db.get_all_assets():
            exists = False
            type_dir = os.path.join(self.assets_dir, f"{asset.type}s")
            if os.path.isdir(type_dir):
                for root, _dirs, files in os.walk(type_dir):
                    if asset.file in files:
                        exists = True
                        break
            if not exists:
                self.db.delete_asset(asset.id)
                deleted += 1
        return deleted

    def _process_file(self, full_path: str, filename: str, asset_type: str) -> bool:
        tags = _extract_tags_from_name(filename)

        parent_dir = Path(full_path).parent.name
        if parent_dir and parent_dir not in {"videos", "images", "bgm", "voice"}:
            if parent_dir not in tags:
                tags.append(parent_dir)

        tags = list(dict.fromkeys(tags))

        duration: Optional[float] = None
        width, height = 0, 0

        if asset_type in ("video", "image"):
            if asset_type == "video":
                duration, width, height = _get_video_info(full_path)
            else:
                _, width, height = _get_video_info(full_path)
                duration = 5.0
        else:
            duration = _get_audio_info(full_path)

        asset = Asset(
            file=filename,
            type=asset_type,
            duration=duration,
            width=width,
            height=height,
            tags=tags,
            file_size=_get_file_size(full_path),
        )
        self.db.add_asset(asset)
        return True
