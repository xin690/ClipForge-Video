import os
import pytest
from core.ffmpeg import (
    FFmpegBuilder, _decode_ffmpeg, check_ffmpeg, has_libass,
    create_test_video, create_test_audio,
)


class TestDecodeFFmpeg:
    def test_decode_utf8(self):
        result = _decode_ffmpeg(b"hello ffmpeg")
        assert result == "hello ffmpeg"

    def test_decode_ascii(self):
        result = _decode_ffmpeg(b"Stream #0:0 Video: h264")
        assert "Stream" in result

    def test_decode_gbk_fallback(self):
        result = _decode_ffmpeg(b"\xce\xc4\xbc\xfe")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_decode_invalid_fallback(self):
        result = _decode_ffmpeg(b"\xff\xfe\x00\x01")
        assert isinstance(result, str)

    def test_decode_empty(self):
        result = _decode_ffmpeg(b"")
        assert result == ""


class TestFFmpegBuilder:
    def test_build_simple(self):
        cmd = (
            FFmpegBuilder("ffmpeg")
            .input("in.mp4")
            .output("out.mp4", {"c:v": "libx264", "preset": "fast"})
            .build()
        )
        assert cmd[0] == "ffmpeg"
        assert "-i" in cmd
        assert "in.mp4" in cmd
        assert "out.mp4" in cmd

    def test_build_list_options(self):
        cmd = (
            FFmpegBuilder()
            .output("out.mp4", {"map": ["0:v", "[aout]"]})
            .build()
        )
        assert cmd.count("-map") == 2
        map_idx = cmd.index("-map")
        assert cmd[map_idx + 1] == "0:v"
        assert cmd[map_idx + 3] == "[aout]"

    def test_build_filter_complex(self):
        cmd = (
            FFmpegBuilder()
            .input("a.mp4")
            .input("b.mp4")
            .filter_complex("[0:v][1:v]concat=n=2[v]")
            .output("out.mp4", {"map": "[v]"})
            .build()
        )
        assert "-filter_complex" in cmd
        fc_idx = cmd.index("-filter_complex")
        assert "concat" in cmd[fc_idx + 1]

    def test_build_overwrite(self):
        cmd = FFmpegBuilder().input("i.mp4").output("o.mp4", {}).build()
        assert "-y" in cmd

    def test_build_reset(self):
        builder = FFmpegBuilder().input("i.mp4").output("o.mp4", {})
        builder.reset()
        cmd = builder.build()
        assert "-i" not in cmd
        assert "o.mp4" not in cmd

    def test_build_global_options(self):
        cmd = (
            FFmpegBuilder()
            .global_option("progress", "pipe:1")
            .input("i.mp4")
            .output("o.mp4", {})
            .build()
        )
        assert "-progress" in cmd

    def test_build_multi_input(self):
        cmd = (
            FFmpegBuilder()
            .input("v1.mp4")
            .input("v2.mp4")
            .output("out.mp4", {"c:v": "copy"})
            .build()
        )
        assert cmd.count("-i") == 2
        in1 = cmd.index("v1.mp4")
        in2 = cmd.index("v2.mp4")
        assert cmd[in1 - 1] == "-i"
        assert cmd[in2 - 1] == "-i"


class TestFFmpegDetection:
    def _ffmpeg_available(self):
        import subprocess
        try:
            import subprocess
            subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
            return True
        except Exception:
            return False

    def test_check_ffmpeg(self):
        available = check_ffmpeg()
        assert isinstance(available, bool)

    def test_has_libass_type(self):
        result = has_libass()
        assert isinstance(result, bool)

    def test_create_test_video(self, temp_dir):
        if not self._ffmpeg_available():
            pytest.skip("FFmpeg not available")
        out = temp_dir + "/test.mp4"
        ok = create_test_video(out, duration=1, color="blue")
        assert ok
        assert os.path.getsize(out) > 0

    def test_create_test_audio(self, temp_dir):
        if not self._ffmpeg_available():
            pytest.skip("FFmpeg not available")
        out = temp_dir + "/test.wav"
        ok = create_test_audio(out, duration=1)
        assert ok
        assert os.path.getsize(out) > 0
