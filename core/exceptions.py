from typing import Optional


class ClipForgeError(Exception):

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class FFmpegError(ClipForgeError):

    def __init__(
        self,
        message: str,
        command: Optional[list[str]] = None,
        stderr: str = "",
        returncode: int = -1,
    ):
        self.command = command or []
        self.stderr = stderr
        self.returncode = returncode
        super().__init__(message)


class AssetNotFoundError(ClipForgeError):

    def __init__(
        self,
        message: str,
        asset_file: str = "",
        asset_type: str = "",
        keywords: Optional[list[str]] = None,
    ):
        self.asset_file = asset_file
        self.asset_type = asset_type
        self.keywords = keywords or []
        super().__init__(message)


class TTSError(ClipForgeError):

    def __init__(
        self,
        message: str,
        text: str = "",
        voice: str = "",
        engine: str = "",
    ):
        self.text = text
        self.voice = voice
        self.engine = engine
        super().__init__(message)


class PipelineError(ClipForgeError):

    def __init__(
        self,
        step,  # PipelineStep (avoid circular import, use Any)
        message: str,
        cause: Optional[Exception] = None,
    ):
        self.step = step
        self.cause = cause
        super().__init__(f"[{step.value}] {message}")


class ConfigError(ClipForgeError):

    def __init__(self, message: str, key: str = "", expected: str = ""):
        self.key = key
        self.expected = expected
        super().__init__(message)


class RenderError(ClipForgeError):

    def __init__(self, message: str, clip: str = "", error: str = ""):
        self.clip = clip
        self.error = error
        super().__init__(message)
