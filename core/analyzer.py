import json
import subprocess
from pathlib import Path
from typing import Optional


def _run_probe(filepath: str, ffprobe_path: str = "ffprobe") -> Optional[dict]:
    try:
        result = subprocess.run(
            [ffprobe_path, "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", str(filepath)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except Exception:
        return None


class ContentAnalyzer:

    @staticmethod
    def analyze_video(filepath: str) -> list[str]:
        tags: list[str] = []
        probe = _run_probe(filepath)
        if not probe:
            return tags

        video_stream = None
        for stream in probe.get("streams", []):
            if stream.get("codec_type") == "video":
                video_stream = stream
                break

        if video_stream:
            w = video_stream.get("width", 0)
            h = video_stream.get("height", 0)
            if w >= 3840:
                tags.append("res:4k")
            elif w >= 2560:
                tags.append("res:2k")
            elif w >= 1920:
                tags.append("res:1080p")
            elif w >= 1280:
                tags.append("res:720p")
            elif w > 0:
                tags.append("res:low")

            fps_str = video_stream.get("r_frame_rate", "0/1")
            fps = 0.0
            if "/" in fps_str:
                parts = fps_str.split("/")
                try:
                    fps = float(parts[0]) / float(parts[1])
                except (ValueError, ZeroDivisionError):
                    pass
            if fps >= 50:
                tags.append("motion:smooth")
                tags.append("dynamic")
            elif fps >= 25:
                tags.append("motion:standard")
            elif fps >= 20:
                tags.append("motion:cinematic")
            elif fps > 0:
                tags.append("motion:low")

            pix_fmt = video_stream.get("pix_fmt", "")
            if "yuv420p10" in pix_fmt or "yuv422p10" in pix_fmt:
                tags.append("color:hdr")
            elif "yuv444" in pix_fmt:
                tags.append("color:full")

            bits = video_stream.get("bits_per_raw_sample", "")
            if bits == "10" or bits == "12":
                tags.append("color:deep")

        fmt = probe.get("format", {})
        duration_s = float(fmt.get("duration", 0) or 0)
        if duration_s > 0:
            if duration_s <= 5:
                tags.append("duration:short")
            elif duration_s <= 15:
                tags.append("duration:medium")
            else:
                tags.append("duration:long")

        return tags

    @staticmethod
    def analyze_image(filepath: str) -> list[str]:
        tags: list[str] = []
        probe = _run_probe(filepath)
        if not probe:
            return tags

        video_stream = None
        for stream in probe.get("streams", []):
            if stream.get("codec_type") == "video":
                video_stream = stream
                break

        if video_stream:
            w = video_stream.get("width", 0)
            h = video_stream.get("height", 0)
            if w >= 3840:
                tags.append("res:4k")
            elif w >= 2560:
                tags.append("res:2k")
            elif w >= 1920:
                tags.append("res:1080p")
            elif w >= 1280:
                tags.append("res:720p")
            elif w > 0:
                tags.append("res:low")

            ratio = w / max(h, 1)
            if ratio > 1.9:
                tags.append("aspect:wide")
            elif ratio < 0.6:
                tags.append("aspect:tall")
            elif 0.9 <= ratio <= 1.1:
                tags.append("aspect:square")

        return tags

    @staticmethod
    def analyze_bgm(filepath: str) -> list[str]:
        tags: list[str] = []
        probe = _run_probe(filepath)
        if not probe:
            return tags

        audio_stream = None
        for stream in probe.get("streams", []):
            if stream.get("codec_type") == "audio":
                audio_stream = stream
                break

        if audio_stream:
            sr = int(audio_stream.get("sample_rate", 0) or 0)
            if sr >= 96000:
                tags.append("audio:hires")
            elif sr >= 44100:
                tags.append("audio:standard")
            elif sr > 0:
                tags.append("audio:lowrate")

            ch = audio_stream.get("channels", 0)
            if ch >= 2:
                tags.append("audio:stereo")
            elif ch == 1:
                tags.append("audio:mono")

            codec = audio_stream.get("codec_name", "")
            if codec in ("flac", "alac", "pcm_s16le", "pcm_s24le"):
                tags.append("audio:lossless")
            elif codec in ("aac", "mp3", "opus", "vorbis"):
                tags.append("audio:lossy")

        return tags
