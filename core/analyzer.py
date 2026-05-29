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

        tags.extend(ContentAnalyzer._detect_scene_changes(filepath))
        tags.extend(ContentAnalyzer._detect_dominant_color(filepath))
        tags.extend(ContentAnalyzer._detect_black_bars(filepath))

        return tags

    @staticmethod
    def _detect_scene_changes(filepath: str) -> list[str]:
        import subprocess, json
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_frames", "-read_intervals", "%+#50",
                 str(filepath)],
                capture_output=True, text=True, timeout=15,
            )
            data = json.loads(result.stdout)
            frames = data.get("frames", [])
            if len(frames) < 2:
                return []
            changes = sum(1 for f in frames if f.get("pict_type") == "I")
            ratio = changes / max(len(frames), 1)
            if ratio > 0.3:
                return ["scene:high", "dynamic"]
            elif ratio < 0.1:
                return ["scene:low", "static"]
            return ["scene:medium"]
        except Exception:
            return []

    @staticmethod
    def _detect_dominant_color(filepath: str) -> list[str]:
        import subprocess, os, tempfile
        from PIL import Image
        import colorsys
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = tmp.name
            subprocess.run(
                ["ffmpeg", "-y", "-ss", "1", "-i", str(filepath),
                 "-vframes", "1", "-q:v", "2", tmp_path],
                capture_output=True, timeout=10,
            )
            if not os.path.exists(tmp_path):
                return []
            img = Image.open(tmp_path).convert("RGB").resize((64, 64))
            pixels = list(img.getdata())
            buckets = {"red": 0, "orange": 0, "yellow": 0, "green": 0,
                        "cyan": 0, "blue": 0, "purple": 0, "pink": 0,
                        "gray": 0, "brown": 0}
            bright_count = 0
            dark_count = 0
            for r, g, b in pixels:
                h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                if v > 0.7:
                    bright_count += 1
                elif v < 0.3:
                    dark_count += 1
                if s < 0.2:
                    buckets["gray"] += 1
                    continue
                h_deg = h * 360
                if h_deg < 20 or h_deg >= 340:
                    buckets["red"] += 1
                elif h_deg < 45:
                    buckets["orange"] += 1
                elif h_deg < 75:
                    buckets["yellow"] += 1
                elif h_deg < 160:
                    buckets["green"] += 1
                elif h_deg < 200:
                    buckets["cyan"] += 1
                elif h_deg < 280:
                    buckets["blue"] += 1
                elif h_deg < 330:
                    buckets["purple"] += 1
                else:
                    buckets["pink"] += 1
            total = len(pixels)
            sorted_colors = sorted(buckets.items(), key=lambda x: -x[1])
            tags = [f"color:{sorted_colors[0][0]}"]
            if sorted_colors[0][1] / total > 0.5:
                tags.append(f"color:dominant_{sorted_colors[0][0]}")
            if bright_count / total > 0.6:
                tags.append("color:bright")
            elif dark_count / total > 0.6:
                tags.append("color:dark")
            return tags
        except Exception:
            return []
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    @staticmethod
    def _detect_black_bars(filepath: str) -> list[str]:
        import subprocess, re
        try:
            result = subprocess.run(
                ["ffmpeg", "-i", str(filepath), "-t", "2",
                 "-vf", "cropdetect=24:16:0", "-f", "null", "-"],
                capture_output=True, text=True, timeout=15,
            )
            matches = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", result.stderr)
            if not matches:
                return []
            w, h, x, y = int(matches[-1][0]), int(matches[-1][1]), int(matches[-1][2]), int(matches[-1][3])
            probe = _run_probe(filepath)
            orig_w, orig_h = 1920, 1080
            if probe:
                for s in probe.get("streams", []):
                    if s.get("codec_type") == "video":
                        orig_w = s.get("width", 1920)
                        orig_h = s.get("height", 1080)
                        break
            if x > 0 or y > 0:
                tags = ["letterbox"]
                if orig_w / orig_h > 2.0:
                    tags.append("aspect:ultrawide")
                elif orig_w / orig_h < 1.5:
                    tags.append("aspect:standard")
                return tags
            return []
        except Exception:
            return []

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
