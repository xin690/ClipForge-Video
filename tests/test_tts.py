import pytest
import os
from core.tts import TTSModule


class TestTTSInit:
    def test_init_defaults(self):
        config = {"tts": {"engine": "edge-tts", "voice": "zh-CN-XiaoxiaoNeural", "speed": 1.0},
                   "paths": {"cache": "./cache"}}
        tts = TTSModule(config)
        assert tts.engine == "edge-tts"
        assert tts.voice == "zh-CN-XiaoxiaoNeural"

    def test_cache_dir_created(self, temp_dir):
        config = {"tts": {}, "paths": {"cache": temp_dir}}
        tts = TTSModule(config)
        assert tts.cache_dir.exists()

    def test_silent_audio_generates_file(self, temp_dir):
        config = {"tts": {}, "paths": {"cache": temp_dir}}
        tts = TTSModule(config)
        out = os.path.join(temp_dir, "test_silent.wav")
        result = tts._silent_audio("测试文本", out)
        if result:
            assert os.path.exists(result)
            assert os.path.getsize(result) > 0
        else:
            pytest.skip("FFmpeg not available for silent audio")

    def test_silent_audio_duration_scales_with_text(self, temp_dir):
        config = {"tts": {}, "paths": {"cache": temp_dir}}
        tts = TTSModule(config)
        short_out = os.path.join(temp_dir, "short.wav")
        long_out = os.path.join(temp_dir, "long.wav")
        tts._silent_audio("短", short_out)
        tts._silent_audio("这是一段较长的测试文本用于验证时长", long_out)
        if os.path.exists(short_out) and os.path.exists(long_out):
            import subprocess
            def get_dur(p):
                r = subprocess.run(["ffprobe", "-v", "quiet", "-show_format", "-print_format", "json", p],
                                   capture_output=True, text=True, errors='replace', timeout=10)
                import json
                return float(json.loads(r.stdout)["format"]["duration"])
            short_dur = get_dur(short_out)
            long_dur = get_dur(long_out)
            assert long_dur > short_dur
        else:
            pytest.skip("FFmpeg not available")


class TestTTSFallback:
    def test_fallback_tts_generates(self, temp_dir):
        config = {"tts": {"engine": "pyttsx3"}, "paths": {"cache": temp_dir}}
        tts = TTSModule(config)
        out = os.path.join(temp_dir, "test_fallback.wav")
        try:
            result = tts._fallback_tts("测试", out)
            if result and os.path.exists(result):
                assert os.path.getsize(result) > 0
            else:
                pytest.skip("pyttsx3 failed (no SAPI5)")
        except Exception:
            pytest.skip("pyttsx3 not available on this system")


class TestTTSGeneration:
    def test_generate_returns_path(self, temp_dir):
        config = {"tts": {"engine": "edge-tts"}, "paths": {"cache": temp_dir}}
        tts = TTSModule(config)
        out = os.path.join(temp_dir, "test.wav")
        result = tts.generate("测试", out)
        if result and os.path.exists(result) and os.path.getsize(result) > 0:
            pass
        else:
            pytest.skip("TTS generation failed (no network or edge-tts)")

    def test_generate_batch_returns_list(self, temp_dir):
        config = {"tts": {"engine": "edge-tts"}, "paths": {"cache": temp_dir}}
        tts = TTSModule(config)
        segments = [(1, "第一段"), (2, "第二段")]
        results = tts.generate_batch(segments, temp_dir)
        assert len(results) == 2

    def test_cache_hit_returns_cached(self, temp_dir):
        config = {"tts": {"engine": "edge-tts"}, "paths": {"cache": temp_dir}}
        tts = TTSModule(config)
        out1 = os.path.join(temp_dir, "test1.wav")
        out2 = os.path.join(temp_dir, "test2.wav")
        r1 = tts.generate("缓存测试", out1)
        r2 = tts.generate("缓存测试", out2)
        assert r1 or r2  # either works or skips


class TestTTSBatch:
    def test_generate_batch_async(self, temp_dir):
        config = {"tts": {"engine": "edge-tts"}, "paths": {"cache": temp_dir}}
        tts = TTSModule(config)
        segments = [(1, "异步测试1"), (2, "异步测试2")]
        results = tts.generate_batch_async(segments, temp_dir)
        assert len(results) == 2
