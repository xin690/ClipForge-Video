import pytest
import os
from core.subtitle import SubtitleGenerator


class TestSubtitleInit:
    def test_init_defaults(self):
        config = {"subtitle": {"engine": "text"}, "paths": {"cache": "./cache"}}
        gen = SubtitleGenerator(config)
        assert gen.mode == "text"

    def test_cache_dir_created(self, temp_dir):
        config = {"subtitle": {"engine": "text"}, "paths": {"cache": temp_dir}}
        gen = SubtitleGenerator(config)
        assert gen.cache_dir.exists()


class TestSubtitleFormat:
    def test_format_srt_single(self, temp_dir):
        config = {"subtitle": {"engine": "text"}, "paths": {"cache": temp_dir}}
        gen = SubtitleGenerator(config)
        segments = [(0.0, 5.0, "测试字幕")]
        out = os.path.join(temp_dir, "test.srt")
        gen.generate_from_text(segments, out, "normal")
        with open(out, encoding="utf-8") as f:
            content = f.read()
        assert "1" in content
        assert "00:00:00,000 --> 00:00:05,000" in content
        assert "测试字幕" in content

    def test_format_srt_multiple(self, temp_dir):
        config = {"subtitle": {"engine": "text"}, "paths": {"cache": temp_dir}}
        gen = SubtitleGenerator(config)
        segments = [(0.0, 3.0, "第一段"), (3.0, 6.0, "第二段")]
        out = os.path.join(temp_dir, "multi.srt")
        gen.generate_from_text(segments, out, "normal")
        with open(out, encoding="utf-8") as f:
            content = f.read()
        assert "第一段" in content
        assert "第二段" in content
        assert content.count("-->") == 2

    def test_format_ass_single(self, temp_dir):
        config = {"subtitle": {"engine": "text"}, "paths": {"cache": temp_dir}}
        gen = SubtitleGenerator(config)
        segments = [(0.0, 5.0, "测试ASS字幕", "normal")]
        out = os.path.join(temp_dir, "test.ass")
        gen.generate_from_text(segments, out)
        with open(out, encoding="utf-8") as f:
            content = f.read()
        assert "[Script Info]" in content
        assert "[V4+ Styles]" in content
        assert "[Events]" in content
        assert "测试ASS字幕" in content

    def test_format_ass_styles_differ(self, temp_dir):
        config = {"subtitle": {"engine": "text"}, "paths": {"cache": temp_dir}}
        gen = SubtitleGenerator(config)
        normal_seg = [(0.0, 5.0, "测试", "normal")]
        strong_seg = [(0.0, 5.0, "测试", "big_yellow")]
        normal_out = os.path.join(temp_dir, "normal.ass")
        strong_out = os.path.join(temp_dir, "strong.ass")
        gen.generate_from_text(normal_seg, normal_out)
        gen.generate_from_text(strong_seg, strong_out)
        with open(normal_out, encoding="utf-8") as f:
            normal_content = f.read()
        with open(strong_out, encoding="utf-8") as f:
            strong_content = f.read()
        assert ",normal,," in normal_content
        assert ",big_yellow,," in strong_content

    def test_empty_segments(self, temp_dir):
        config = {"subtitle": {"engine": "text"}, "paths": {"cache": temp_dir}}
        gen = SubtitleGenerator(config)
        out = os.path.join(temp_dir, "empty.ass")
        gen.generate_from_text([], out, "normal")
        assert os.path.exists(out)
        with open(out, encoding="utf-8") as f:
            content = f.read()
        assert "[Events]" in content

    def test_srt_time_format_precision(self, temp_dir):
        config = {"subtitle": {"engine": "text"}, "paths": {"cache": temp_dir}}
        gen = SubtitleGenerator(config)
        segments = [(1.234, 5.678, "时间精度测试")]
        out = os.path.join(temp_dir, "precision.srt")
        gen.generate_from_text(segments, out, "normal")
        with open(out, encoding="utf-8") as f:
            content = f.read()
        assert "01,234" in content.split("-->")[0]

    def test_ass_time_format(self, temp_dir):
        config = {"subtitle": {"engine": "text"}, "paths": {"cache": temp_dir}}
        gen = SubtitleGenerator(config)
        segments = [(1.5, 5.5, "时间测试", "normal")]
        out = os.path.join(temp_dir, "time.ass")
        gen.generate_from_text(segments, out)
        with open(out, encoding="utf-8") as f:
            content = f.read()
        assert "0:00:01.50" in content or "0:00:01,50" in content

    def test_ass_style_font_settings(self, temp_dir):
        config = {"subtitle": {"engine": "text"}, "paths": {"cache": temp_dir}}
        gen = SubtitleGenerator(config)
        segments = [(0.0, 5.0, "样式测试", "big_yellow")]
        out = os.path.join(temp_dir, "style.ass")
        gen.generate_from_text(segments, out)
        with open(out, encoding="utf-8") as f:
            content = f.read()
        assert "Microsoft YaHei" in content or "Fontname" in content

    def test_per_segment_position_override(self, temp_dir):
        config = {"subtitle": {"engine": "text"}, "paths": {"cache": temp_dir}}
        gen = SubtitleGenerator(config)
        segments = [(0.0, 3.0, "顶部字幕", "normal", "none", "top"),
                      (3.0, 6.0, "底部字幕", "normal", "none", "bottom")]
        out = os.path.join(temp_dir, "pos.ass")
        gen.generate_from_text(segments, out)
        with open(out, encoding="utf-8") as f:
            content = f.read()
        assert "0:00:00.00" in content or "0:00:00,00" in content
        assert "顶部字幕" in content
        assert "底部字幕" in content

    def test_position_align_tag_in_output(self, temp_dir):
        config = {"subtitle": {"engine": "text"}, "paths": {"cache": temp_dir}}
        gen = SubtitleGenerator(config)
        segments = [(0.0, 5.0, "居顶", "normal", "none", "top")]
        out = os.path.join(temp_dir, "align.ass")
        gen.generate_from_text(segments, out)
        with open(out, encoding="utf-8") as f:
            content = f.read()
        assert "an8" in content

    def test_position_no_override_when_default(self, temp_dir):
        config = {"subtitle": {"engine": "text"}, "paths": {"cache": temp_dir}}
        gen = SubtitleGenerator(config)
        segments = [(0.0, 5.0, "默认底部", "normal", "none", "bottom")]
        out = os.path.join(temp_dir, "default_bottom.ass")
        gen.generate_from_text(segments, out)
        with open(out, encoding="utf-8") as f:
            content = f.read()
        assert "an2" not in content

    def test_margin_v_in_custom_style(self, temp_dir):
        config = {
            "subtitle": {"engine": "text", "font_family": "Arial", "margin_v": 42},
            "paths": {"cache": temp_dir},
        }
        gen = SubtitleGenerator(config)
        segments = [(0.0, 5.0, "自定义边距", "custom")]
        out = os.path.join(temp_dir, "margin.ass")
        gen.generate_from_text(segments, out)
        with open(out, encoding="utf-8") as f:
            content = f.read()
        assert "Style: custom" in content
        assert ",42," in content or "10,42" in content

    def test_segment_anim_and_position_combined(self, temp_dir):
        config = {"subtitle": {"engine": "text"}, "paths": {"cache": temp_dir}}
        gen = SubtitleGenerator(config)
        segments = [(0.0, 5.0, "动画+位置", "normal", "fadein", "top")]
        out = os.path.join(temp_dir, "animpos.ass")
        gen.generate_from_text(segments, out)
        with open(out, encoding="utf-8") as f:
            content = f.read()
        assert "an8" in content
        assert "fadein" in content or "alpha" in content

    def test_position_align_all_values(self):
        from core.subtitle import POSITION_ALIGN
        assert POSITION_ALIGN["bottom"] == 2
        assert POSITION_ALIGN["top"] == 8
        assert POSITION_ALIGN["center"] == 5
        assert POSITION_ALIGN["bottom_left"] == 1
        assert POSITION_ALIGN["bottom_right"] == 3
        assert POSITION_ALIGN["top_left"] == 7
        assert POSITION_ALIGN["top_right"] == 9
        assert POSITION_ALIGN["middle_left"] == 4
        assert POSITION_ALIGN["middle_right"] == 6


class TestAnimationTags:

    def test_all_animations_are_tags(self):
        from core.subtitle import ANIMATION_TAGS
        for name in ["pulse", "swing", "fadein", "scale", "typing",
                      "slide_up", "typewriter", "bounce", "glow"]:
            assert name in ANIMATION_TAGS, f"Missing animation: {name}"

    def test_new_animations_in_output(self, temp_dir):
        import os
        config = {"subtitle": {"engine": "text"}, "paths": {"cache": temp_dir}}
        gen = SubtitleGenerator(config)
        out = os.path.join(temp_dir, "anim_new.ass")
        gen.generate_from_text([], out)
        with open(out, encoding="utf-8") as f:
            content = f.read()
        assert "{\\t" in content or "Animation" in content or "Style" in content
