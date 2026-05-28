import os
import sys
import yaml
from pathlib import Path
from typing import Any


_CONFIG: dict[str, Any] | None = None
_CONFIG_PATH: str | None = None


def load_config(config_path: str | None = None) -> dict[str, Any]:
    global _CONFIG, _CONFIG_PATH

    if config_path is None:
        config_path = os.environ.get("CLIPFORGE_CONFIG", "")
        if not config_path:
            config_path = os.path.join(os.path.dirname(sys.argv[0]), "config.yaml") if getattr(sys, 'frozen', False) else "config.yaml"

    _CONFIG_PATH = config_path
    path = Path(config_path)

    if not path.exists():
        _CONFIG = _default_config()
        save_config()
        return _CONFIG

    with open(path, encoding="utf-8") as f:
        _CONFIG = yaml.safe_load(f) or _default_config()
    return _CONFIG


def get_config() -> dict[str, Any]:
    global _CONFIG
    if _CONFIG is None:
        return load_config()
    return _CONFIG


def save_config(config: dict[str, Any] | None = None) -> None:
    global _CONFIG
    if config is not None:
        _CONFIG = config
    if _CONFIG is None:
        return
    path = Path(_CONFIG_PATH) if _CONFIG_PATH else Path("config.yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(_CONFIG, f, default_flow_style=False, allow_unicode=True)


def get(key: str, default: Any = None) -> Any:
    cfg = get_config()
    parts = key.split(".")
    for part in parts:
        if isinstance(cfg, dict):
            cfg = cfg.get(part)
        else:
            return default
    return cfg if cfg is not None else default


def _default_config() -> dict[str, Any]:
    return {
        "app": {"name": "ClipForge", "version": "0.3.0"},
        "paths": {
            "assets": "./assets",
            "scripts": "./scripts",
            "output": "./output",
            "cache": "./cache",
            "database": "./database/clipforge.db",
        },
        "video": {"width": 1920, "height": 1080, "fps": 30, "preset": "veryfast", "crf": 23},
        "tts": {"engine": "edge-tts", "voice": "zh-CN-XiaoxiaoNeural", "speed": 1.0},
        "subtitle": {
            "engine": "text",
            "whisper_model": "tiny",
            "device": "cpu",
            "font_family": "Microsoft YaHei",
            "font_size": 36,
            "font_color": "#FFFFFF",
            "bold": False,
            "outline": 2,
            "shadow": 1,
            "position": "bottom",
            "margin_v": 10,
            "animation": "none",
        },
        "ai": {
            "enabled": False, "provider": "openai", "api_key": "",
            "model": "gpt-4o-mini",
            "max_versions": 2, "critique_enabled": True,
        },
        "downloader": {"provider": "pexels", "api_key": "", "max_per_query": 3, "min_width": 1920, "timeout": 120},
        "bgm": {"volume": 0.3},
        "logging": {"level": "INFO"},
        "qa": {
            "preset": "tiktok", "auto_checks": True,
            "presets": {
                "tiktok": {
                    "segment_min": 3, "segment_max": 8,
                    "duration_per_seg_min": 2, "duration_per_seg_max": 10,
                    "total_duration_max": 120,
                    "text_min_len": 10, "text_max_len": 150,
                    "min_keywords": 2, "duration_tolerance": 5,
                },
                "youtube": {
                    "segment_min": 3, "segment_max": 15,
                    "duration_per_seg_min": 3, "duration_per_seg_max": 15,
                    "total_duration_max": 1200,
                    "text_min_len": 15, "text_max_len": 200,
                    "min_keywords": 2, "duration_tolerance": 10,
                },
                "commerce": {
                    "segment_min": 2, "segment_max": 6,
                    "duration_per_seg_min": 3, "duration_per_seg_max": 12,
                    "total_duration_max": 60,
                    "text_min_len": 5, "text_max_len": 100,
                    "min_keywords": 3, "duration_tolerance": 3,
                },
            },
        },
    }


def resolve_path(relative_path: str) -> str:
    cfg = get_config()
    base = cfg.get("paths", {}).get("assets", "./assets")
    app_dir = os.path.dirname(os.path.abspath(_CONFIG_PATH)) if _CONFIG_PATH else os.getcwd()
    return os.path.normpath(os.path.join(app_dir, relative_path))
