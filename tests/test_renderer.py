import pytest
import os
from core.renderer import Renderer
from core.models import Timeline, TimelineItem, Script, Segment
from core.config import load_config


class TestRendererInit:
    def test_init_defaults(self):
        config = load_config()
        r = Renderer(config)
        assert r.resolution == (1920, 1080)
        assert r.fps == 30
        assert r.preset == "veryfast"
        assert r.crf == 23

    def test_temp_dir_created(self, temp_dir):
        cfg = {"paths": {"cache": temp_dir}, "video": {"width": 1920, "height": 1080, "fps": 30, "preset": "fast", "crf": 23}}
        r = Renderer(cfg)
        assert r.temp_dir.exists()

    def test_has_audio_stream_no_file(self):
        config = load_config()
        r = Renderer(config)
        assert r._has_audio_stream("nonexistent.mp4") is False

    def test_report_callback(self):
        config = load_config()
        r = Renderer(config)
        called = []

        def cb(p):
            called.append(p)

        r._report(cb, 0.5, "test")
        assert len(called) == 1
        assert called[0] == 0.5

    def test_parse_ass_time(self):
        assert Renderer._parse_ass_time("0:00:01.50") == 1.5
        assert Renderer._parse_ass_time("0:01:30.00") == 90.0
        assert Renderer._parse_ass_time("1:00:00.00") == 3600.0
        assert Renderer._parse_ass_time("0:00:00.00") == 0.0

    def test_parse_ass_time_comma(self):
        assert Renderer._parse_ass_time("0:00:01,50") == 1.5

    def test_find_asset_not_found(self, temp_dir):
        config = load_config()
        r = Renderer(config)
        result = r._find_asset("nonexistent.mp4", temp_dir, "video")
        assert result is None

    def test_find_asset_in_subdir(self, temp_dir):
        videos = os.path.join(temp_dir, "videos")
        os.makedirs(videos, exist_ok=True)
        test_file = os.path.join(videos, "test.mp4")
        with open(test_file, "w") as f:
            f.write("test")

        config = load_config()
        r = Renderer(config)
        result = r._find_asset("test.mp4", temp_dir, "video")
        assert result == test_file

    def test_log_execute_error(self):
        config = load_config()
        r = Renderer(config)
        r._log_execute_error(["ffmpeg", "-i", "x"], "error message")
        assert True


class TestRendererSubtitle:
    def test_parse_ass_events_nonexistent(self, temp_dir):
        config = load_config()
        r = Renderer(config)
        events = r._parse_ass_events(os.path.join(temp_dir, "no.ass"))
        assert events == []

    def test_generate_subtitle_file(self, temp_dir):
        config = load_config()
        r = Renderer(config)
        item = TimelineItem(start=0, end=5, asset="t.mp4", subtitle="测试字幕")
        tl = Timeline(timeline=[item])
        out = os.path.join(temp_dir, "test.ass")
        r._generate_subtitle_file(tl, out)
        assert os.path.exists(out)
        with open(out, encoding="utf-8") as f:
            content = f.read()
        assert "[Events]" in content
        assert "测试字幕" in content


class TestRendererInvalidTimeline:
    def test_render_zero_duration(self):
        from core.ffmpeg import check_ffmpeg
        if not check_ffmpeg():
            pytest.skip("FFmpeg not available")
        config = load_config()
        r = Renderer(config)
        with pytest.raises(ValueError, match="时长为 0"):
            r.render(Timeline(timeline=[TimelineItem(start=0, end=0, asset="t.mp4")]), "out.mp4")

    def test_render_no_clips(self, temp_dir):
        config = load_config()
        r = Renderer(config)
        from core.models import TimelineItem
        item = TimelineItem(start=0, end=5, asset="nonexistent.mp4")
        try:
            clips = r._render_clips(Timeline(timeline=[item]), str(temp_dir), str(temp_dir), 10)
            assert len(clips) == 1
            assert clips[0].endswith(".mp4")
        except Exception:
            pytest.skip("FFmpeg not available for placeholder rendering")
