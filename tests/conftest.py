import pytest
import tempfile
import os
import json
import shutil


@pytest.fixture(autouse=True)
def _no_custom_subtitle():
    """清除字幕自定义字体，确保 SubtitleStyleRule 使用情绪映射"""
    from core.config import get_config
    cfg = get_config()
    sub = cfg.get("subtitle")
    if sub:
        sub.pop("font_family", None)
        sub.pop("font_color", None)
        sub.pop("font_size", None)
        sub.pop("bold", None)
        sub.pop("outline", None)
        sub.pop("shadow", None)
        sub.pop("position", None)
        sub.pop("animation", None)


@pytest.fixture
def temp_dir():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def sample_script():
    return {
        "title": "测试视频",
        "duration": 15,
        "style": "knowledge",
        "voice": "zh-CN-XiaoxiaoNeural",
        "bgm": "",
        "segments": [
            {"id": 1, "text": "第一段测试文本", "keywords": ["测试", "知识"], "emotion": "normal", "duration": 5},
            {"id": 2, "text": "第二段测试文本", "keywords": ["测试", "重要"], "emotion": "strong", "duration": 6},
            {"id": 3, "text": "第三段测试文本", "keywords": ["测试"], "emotion": "calm", "duration": 4},
        ],
    }


@pytest.fixture
def sample_assets():
    return [
        {"file": "test_video_01.mp4", "type": "video", "duration": 10.0, "tags": ["测试", "知识"], "width": 1920, "height": 1080},
        {"file": "test_video_02.mp4", "type": "video", "duration": 8.0, "tags": ["测试", "重要"], "width": 1920, "height": 1080},
        {"file": "bgm_test.mp3", "type": "bgm", "duration": 30.0, "tags": ["音乐", "背景"], "width": 0, "height": 0},
    ]
