import locale
import os
import re
import subprocess
import time
import threading
import logging
from pathlib import Path
from typing import Optional, Callable

log = logging.getLogger("ffmpeg")

_FFMPEG_CACHE: float | None = None
_FFMPEG_AVAILABLE: bool | None = None
_HAS_LIBASS: bool | None = None
_LIBASS_CACHE: float | None = None
_CACHE_TTL: float = 60.0


class FFmpegBuilder:
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path
        self._inputs: list[tuple[str, dict[str, str | list[str]]]] = []
        self._outputs: list[tuple[str, dict[str, str | list[str]]]] = []
        self._filter_complex: list[str] = []
        self._overwrite = True
        self._global_opts: dict[str, str | list[str]] = {}

    def input(self, path: str, options: dict[str, str | list[str]] | None = None) -> "FFmpegBuilder":
        self._inputs.append((path, options or {}))
        return self

    def output(self, path: str, options: dict[str, str | list[str]] | None = None) -> "FFmpegBuilder":
        self._outputs.append((path, options or {}))
        return self

    def filter_complex(self, filter_str: str) -> "FFmpegBuilder":
        self._filter_complex.append(filter_str)
        return self

    def overwrite(self, value: bool = True) -> "FFmpegBuilder":
        self._overwrite = value
        return self

    def global_option(self, key: str, value: str | list[str]) -> "FFmpegBuilder":
        self._global_opts[key] = value
        return self

    def build(self) -> list[str]:
        cmd = [self.ffmpeg_path]

        if self._overwrite:
            cmd.append("-y")

        for key, value in self._global_opts.items():
            if isinstance(value, list):
                for val in value:
                    cmd.extend([f"-{key}", val])
            else:
                cmd.extend([f"-{key}", value])

        for path, opts in self._inputs:
            for k, v in opts.items():
                if isinstance(v, list):
                    for val in v:
                        cmd.extend([f"-{k}", val])
                else:
                    cmd.extend([f"-{k}", v])
            cmd.extend(["-i", path])

        for filter_str in self._filter_complex:
            cmd.extend(["-filter_complex", filter_str])

        for path, opts in self._outputs:
            for k, v in opts.items():
                if isinstance(v, list):
                    for val in v:
                        cmd.extend([f"-{k}", val])
                else:
                    cmd.extend([f"-{k}", v])
            cmd.append(path)

        return cmd

    def reset(self) -> "FFmpegBuilder":
        self._inputs.clear()
        self._outputs.clear()
        self._filter_complex.clear()
        self._overwrite = True
        self._global_opts.clear()
        return self


def check_ffmpeg() -> bool:
    global _FFMPEG_AVAILABLE, _FFMPEG_CACHE
    now = time.monotonic()
    if _FFMPEG_CACHE is not None and now - _FFMPEG_CACHE < _CACHE_TTL:
        return _FFMPEG_AVAILABLE
    # Prefer full FFmpeg with libass
    for d in [r"C:\ffmpeg\bin", r"C:\Program Files\DownloadHelper CoApp", r"C:\Program Files\ffmpeg\bin"]:
        if os.path.isdir(d) and d not in os.environ.get("PATH", ""):
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        _FFMPEG_AVAILABLE = True
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        _FFMPEG_AVAILABLE = False
    _FFMPEG_CACHE = now
    return _FFMPEG_AVAILABLE


def _decode_ffmpeg(data: bytes) -> str:
    """Try UTF-8 first, fall back to locale encoding with replace."""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        enc = locale.getpreferredencoding(False)
        return data.decode(enc, errors="replace")


def execute(cmd: list[str], timeout: int = 3600, cancel_event: threading.Event | None = None) -> tuple[bool, str]:
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdout_data: list[bytes] = []
        stderr_data: list[bytes] = []

        def _read_pipe(pipe, data_list):
            for line in iter(pipe.readline, b""):
                data_list.append(line)
            pipe.close()

        stdout_thread = threading.Thread(target=_read_pipe, args=(process.stdout, stdout_data))
        stderr_thread = threading.Thread(target=_read_pipe, args=(process.stderr, stderr_data))
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()

        deadline = time.monotonic() + timeout
        while process.poll() is None:
            if cancel_event and cancel_event.is_set():
                process.kill()
                break
            if time.monotonic() > deadline:
                process.kill()
                break
            time.sleep(0.2)

        process.wait(timeout=5)
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)

        if cancel_event and cancel_event.is_set():
            return False, "用户取消"
        if process.returncode != 0:
            return False, _decode_ffmpeg(b"".join(stderr_data))[:1000]
        return True, ""
    except FileNotFoundError:
        return False, "ffmpeg 未找到，请确保已安装并加入 PATH"
    except subprocess.TimeoutExpired:
        return False, "FFmpeg 执行超时"
    except Exception as e:
        return False, str(e)


def execute_with_progress(
    cmd: list[str],
    total_duration: float | None = None,
    progress_callback: Callable[[float], None] | None = None,
    timeout: int = 7200,
    cancel_event: threading.Event | None = None,
) -> tuple[bool, str]:
    _TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+)\.(\d+)")
    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1
        )
        stderr_output: list[str] = []
        stop_reading = threading.Event()

        def _reader():
            assert process.stderr is not None
            for line_bytes in iter(process.stderr.readline, b""):
                if stop_reading.is_set():
                    break
                stderr_output.append(_decode_ffmpeg(line_bytes))
            process.stderr.close()

        reader = threading.Thread(target=_reader, daemon=True)
        reader.start()

        deadline = time.monotonic() + timeout
        while reader.is_alive():
            if cancel_event and cancel_event.is_set():
                process.kill()
                stop_reading.set()
                reader.join(timeout=5)
                return False, "用户取消"
            if time.monotonic() > deadline:
                process.kill()
                stop_reading.set()
                reader.join(timeout=5)
                return False, "FFmpeg 执行超时"
            last_lines = "".join(stderr_output[-20:])
            if total_duration and progress_callback:
                for match in _TIME_RE.finditer(last_lines):
                    h, m, s, ms = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
                    elapsed = h * 3600 + m * 60 + s + ms / 100
                    progress_callback(min(elapsed / total_duration, 1.0))
            time.sleep(0.2)

        process.wait(timeout=5)
        stop_reading.set()
        reader.join(timeout=5)
        if process.returncode == 0:
            return True, ""
        return False, "".join(stderr_output[-20:])
    except FileNotFoundError:
        return False, "ffmpeg 未找到"
    except Exception as e:
        return False, str(e)


def _escape_concat_path(p: str) -> str:
    return p.replace("'", "'\\''")

def concat_demuxer(clip_files: list[str], output_path: str, ffmpeg_path: str = "ffmpeg") -> tuple[bool, str]:
    filelist = "\n".join(f"file '{_escape_concat_path(p)}'" for p in clip_files)
    filelist_path = os.path.join(os.path.dirname(output_path), "_concat_list.txt")
    with open(filelist_path, "w", encoding="utf-8") as f:
        f.write(filelist)

    cmd = [
        ffmpeg_path, "-y", "-f", "concat", "-safe", "0",
        "-fflags", "+genpts",
        "-i", filelist_path,
        "-c", "copy",
        output_path,
    ]
    result, err = execute(cmd)
    if not result:
        log.warning("concat_demuxer (%s) 失败, 回退到 concat filter: %s", "-c copy", err[:200])
        result, err = concat_filter(clip_files, output_path, ffmpeg_path)
    try:
        os.unlink(filelist_path)
    except OSError:
        pass
    return result, err


def concat_filter(clip_files: list[str], output_path: str, ffmpeg_path: str = "ffmpeg") -> tuple[bool, str]:
    """Concatenate clips using the concat filter (re-encodes, but works with any codec combo)."""
    n = len(clip_files)
    inputs = []
    for clip in clip_files:
        inputs.extend(["-i", clip])
    filter_parts = []
    stream_specs = []
    for i in range(n):
        stream_specs.append(f"[{i}:v][{i}:a]")
    filter_parts.append(f"{''.join(stream_specs)}concat=n={n}:v=1:a=1[outv][outa]")
    filter_complex = ";".join(filter_parts)
    cmd = [
        ffmpeg_path, "-y", *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
        "-video_track_timescale", "30000",
        "-movflags", "+faststart",
        output_path,
    ]
    return execute(cmd)


def has_libass() -> bool:
    global _HAS_LIBASS, _LIBASS_CACHE
    now = time.monotonic()
    if _LIBASS_CACHE is not None and now - _LIBASS_CACHE < _CACHE_TTL:
        return _HAS_LIBASS
    try:
        r = subprocess.run(["ffmpeg", "-filters"], capture_output=True, timeout=10)
        _HAS_LIBASS = "ass" in _decode_ffmpeg(r.stdout) and "libass" in _decode_ffmpeg(r.stdout)
    except Exception:
        _HAS_LIBASS = False
    _LIBASS_CACHE = now
    return _HAS_LIBASS


def get_clip_duration(clip_path: str, ffmpeg_path: str = "ffmpeg") -> float:
    """Get duration of a video/audio clip using ffprobe."""
    p = Path(ffmpeg_path)
    ffprobe = str(p.with_name(p.name.replace("ffmpeg", "ffprobe")))
    if ffprobe == ffmpeg_path:
        ffprobe = "ffprobe"
    try:
        r = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", clip_path],
            capture_output=True, timeout=15,
        )
        out = _decode_ffmpeg(r.stdout).strip()
        if r.returncode == 0 and out:
            return float(out)
    except Exception:
        pass
    return 0.0


XFADE_MAP: dict[str, str] = {
    "dissolve":   "dissolve",
    "fade":       "fade",
    "fadeblack":  "fadeblack",
    "fadewhite":  "fadewhite",
    "circleopen": "circleopen",
    "circleclose":"circleclose",
    "radial":     "radial",
    "zoomin":     "zoomin",
    "slide":      "slideleft",
    "smoothleft": "smoothleft",
    "pixelize":   "pixelize",
    "horzopen":   "horzopen",
    "vertopen":   "vertopen",
    "fadegrays":  "fadegrays",
    "wipedown":   "wipedown",
    "wipeleft":   "wipeleft",
    "wiperight":  "wiperight",
    "wipeup":     "wipeup",
    "coverleft":  "coverleft",
    "coverup":    "coverup",
    "coverright": "coverright",
    "coverdown":  "coverdown",
    "revealleft": "revealleft",
    "revealup":   "revealup",
    "revealright":"revealright",
    "revealdown": "revealdown",
    "hlslice":    "hlslice",
    "hrslice":    "hrslice",
    "vuslice":    "vuslice",
    "vdslice":    "vdslice",
    "rectcrop":   "rectcrop",
}

XFADE_DURATION: dict[str, float] = {
    "cut": 0.0, "fade": 0.4, "fadeblack": 0.5, "fadewhite": 0.5,
    "dissolve": 0.5, "circleopen": 0.6, "circleclose": 0.6,
    "radial": 0.5, "zoomin": 0.5, "slide": 0.5,
    "smoothleft": 0.4, "pixelize": 0.6, "horzopen": 0.5, "vertopen": 0.5,
    "fadegrays": 0.5,
    "wipedown": 0.4, "wipeleft": 0.4, "wiperight": 0.4, "wipeup": 0.4,
    "coverleft": 0.5, "coverup": 0.5, "coverright": 0.5, "coverdown": 0.5,
    "revealleft": 0.5, "revealup": 0.5, "revealright": 0.5, "revealdown": 0.5,
    "hlslice": 0.4, "hrslice": 0.4, "vuslice": 0.4, "vdslice": 0.4,
    "rectcrop": 0.5,
}

DEFAULT_TRANS_DURATION = 0.5


def concat_with_xfade(
    clip_files: list[str],
    output_path: str,
    transitions: list[str] | None = None,
    ffmpeg_path: str = "ffmpeg",
    trans_duration: float | None = None,
) -> tuple[bool, str]:
    """
    Concatenate video clips with xfade transitions between them.

    For N clips, transitions[i] (0 <= i < N-1) is the transition type
    between clip_files[i] and clip_files[i+1].

    Supported transitions: cut, dissolve, fade, fadeblack, fadewhite,
    circleopen, circleclose, radial, zoomin, slide, smoothleft,
    pixelize, horzopen, vertopen.
    """
    n = len(clip_files)
    if n < 2:
        return concat_demuxer(clip_files, output_path, ffmpeg_path)

    if transitions is None:
        transitions = ["fade"] * (n - 1)

    durations: list[float] = []
    for clip in clip_files:
        d = get_clip_duration(clip, ffmpeg_path)
        if d <= 0:
            return False, f"无法获取片段时长: {clip}"
        durations.append(d)

    v_filters: list[str] = []
    a_filters: list[str] = []
    prev_v = "0:v"
    prev_a = "0:a"

    for i in range(1, n):
        t_type = transitions[i - 1] if i - 1 < len(transitions) else "fade"
        xf = XFADE_MAP.get(t_type, "fade")
        dur = (trans_duration if trans_duration is not None
               else XFADE_DURATION.get(t_type, DEFAULT_TRANS_DURATION))
        offset = sum(durations[:i])
        if t_type != "cut":
            offset -= dur
        cur_v = f"v{i}"
        cur_a = f"a{i}"
        if t_type != "cut":
            v_filters.append(
                f"[{prev_v}][{i}:v]xfade=transition={xf}:duration={dur}:offset={offset}[{cur_v}]"
            )
        else:
            v_filters.append(
                f"[{prev_v}][{i}:v]concat=n=2:v=1:a=0[{cur_v}]"
            )
        a_filters.append(f"[{prev_a}][{i}:a]acrossfade=d={dur}[{cur_a}]")
        prev_v = cur_v
        prev_a = cur_a

    filter_complex = ";".join(v_filters + a_filters)

    cmd = [ffmpeg_path, "-y"]
    for clip in clip_files:
        cmd.extend(["-i", clip])
    cmd.extend(["-filter_complex", filter_complex])
    cmd.extend(["-map", f"[{prev_v}]", "-map", f"[{prev_a}]"])
    cmd.extend(["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p"])
    cmd.extend(["-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2"])
    cmd.extend(["-video_track_timescale", "30000", "-movflags", "+faststart"])
    cmd.append(output_path)

    return execute(cmd)


def normalize_audio_loudnorm(
    audio_path: str,
    output_path: str,
    ffmpeg_path: str = "ffmpeg",
    i: float = -16.0,
    tp: float = -1.5,
    lra: float = 11.0,
) -> tuple[bool, str]:
    """Normalize audio loudness using EBU R128 loudnorm filter."""
    cmd = [
        ffmpeg_path, "-y", "-i", audio_path,
        "-af", f"loudnorm=I={i}:TP={tp}:LRA={lra}:print_format=summary",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        output_path,
    ]
    return execute(cmd)


def create_test_video(
    output_path: str,
    duration: int = 5,
    width: int = 1920,
    height: int = 1080,
    color: str = "blue",
    ffmpeg_path: str = "ffmpeg",
) -> bool:
    cmd = [
        ffmpeg_path, "-y",
        "-f", "lavfi", "-i", f"color=c={color}:s={width}x{height}:d={duration}:r=30",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        output_path,
    ]
    success, _ = execute(cmd)
    return success


def create_test_audio(
    output_path: str,
    duration: int = 5,
    frequency: int = 440,
    ffmpeg_path: str = "ffmpeg",
) -> bool:
    cmd = [
        ffmpeg_path, "-y",
        "-f", "lavfi", "-i", f"sine=frequency={frequency}:duration={duration}",
        "-acodec", "pcm_s16le",
        output_path,
    ]
    success, _ = execute(cmd)
    return success
