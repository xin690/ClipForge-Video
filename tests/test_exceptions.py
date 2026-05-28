from core.exceptions import (
    ClipForgeError,
    FFmpegError,
    AssetNotFoundError,
    TTSError,
    PipelineError,
    ConfigError,
    RenderError,
)


class TestClipForgeError:

    def test_base_error_message(self):
        err = ClipForgeError("test")
        assert err.message == "test"
        assert str(err) == "test"


class TestFFmpegError:

    def test_basic(self):
        err = FFmpegError("ffmpeg failed", command=["ffmpeg", "-i", "test.mp4"], stderr="error", returncode=1)
        assert err.message == "ffmpeg failed"
        assert err.command == ["ffmpeg", "-i", "test.mp4"]
        assert err.stderr == "error"
        assert err.returncode == 1

    def test_defaults(self):
        err = FFmpegError("oops")
        assert err.command == []
        assert err.stderr == ""
        assert err.returncode == -1

    def test_is_clipforge_error(self):
        err = FFmpegError("fail")
        assert isinstance(err, ClipForgeError)
        assert isinstance(err, Exception)


class TestAssetNotFoundError:

    def test_basic(self):
        err = AssetNotFoundError("not found", asset_file="test.mp4", asset_type="video", keywords=["test"])
        assert err.asset_file == "test.mp4"
        assert err.asset_type == "video"
        assert err.keywords == ["test"]

    def test_defaults(self):
        err = AssetNotFoundError("missing")
        assert err.asset_file == ""
        assert err.asset_type == ""
        assert err.keywords == []


class TestTTSError:

    def test_basic(self):
        err = TTSError("tts failed", text="hello", voice="zh-CN-XiaoxiaoNeural", engine="edge-tts")
        assert err.text == "hello"
        assert err.voice == "zh-CN-XiaoxiaoNeural"
        assert err.engine == "edge-tts"

    def test_defaults(self):
        err = TTSError("fail")
        assert err.text == ""
        assert err.voice == ""
        assert err.engine == ""


class TestConfigError:

    def test_basic(self):
        err = ConfigError("invalid config", key="ai.api_key", expected="non-empty string")
        assert err.key == "ai.api_key"
        assert err.expected == "non-empty string"

    def test_defaults(self):
        err = ConfigError("bad")
        assert err.key == ""
        assert err.expected == ""


class TestRenderError:

    def test_basic(self):
        err = RenderError("render failed", clip="clip_001.mp4", error="encoding error")
        assert err.clip == "clip_001.mp4"
        assert err.error == "encoding error"

    def test_defaults(self):
        err = RenderError("fail")
        assert err.clip == ""
        assert err.error == ""


class TestPipelineError:

    def test_basic(self):
        from core.pipeline import PipelineStep
        err = PipelineError(PipelineStep.LOAD_SCRIPT, "test")
        assert err.step == PipelineStep.LOAD_SCRIPT
        assert err.cause is None
        assert str(err) == "[load_script] test"

    def test_with_cause(self):
        from core.pipeline import PipelineStep
        cause = ValueError("bad data")
        err = PipelineError(PipelineStep.RENDER_VIDEO, "fail", cause)
        assert err.step == PipelineStep.RENDER_VIDEO
        assert err.cause is cause

    def test_is_clipforge_error(self):
        from core.pipeline import PipelineStep
        err = PipelineError(PipelineStep.INIT, "x")
        assert isinstance(err, ClipForgeError)
        assert isinstance(err, Exception)


class TestInheritance:

    def test_all_are_clipforge_errors(self):
        for cls in [FFmpegError, AssetNotFoundError, TTSError, PipelineError, ConfigError, RenderError]:
            assert issubclass(cls, ClipForgeError)
            assert issubclass(cls, Exception)

    def test_clipforge_error_is_exception(self):
        assert issubclass(ClipForgeError, Exception)
