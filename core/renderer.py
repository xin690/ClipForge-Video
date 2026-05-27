import os
import re
import shutil
import subprocess
import tempfile
import traceback
import threading
import logging
from pathlib import Path
from typing import Optional, Callable
from core.models import Timeline, TimelineItem
from core.ffmpeg import (
    FFmpegBuilder, execute, execute_with_progress, concat_filter,
    concat_with_xfade, normalize_audio_loudnorm, get_clip_duration,
    check_ffmpeg, has_libass, _decode_ffmpeg,
)

log = logging.getLogger("renderer")

COLOR_PRESETS: dict[str, str] = {
    "knowledge":     "eq=brightness=0.03:contrast=1.10:saturation=1.05,vignette=PI/4",
    "news":          "eq=brightness=0.05:contrast=1.15:saturation=0.90,vignette=PI/5",
    "entertainment": "eq=brightness=0.04:contrast=1.05:saturation=1.20,vibrance=intensity=0.3",
    "commerce":      "vibrance=intensity=0.3,eq=contrast=1.10,vignette=PI/4.5",
}

try:
    from PIL import Image, ImageDraw, ImageFont
    _HAS_PILLOW = True
except ImportError:
    _HAS_PILLOW = False


class Renderer:
    _has_libass_working: bool | None = None

    def __init__(self, config: dict):
        video_cfg = config.get("video", {})
        self.resolution = (video_cfg.get("width", 1920), video_cfg.get("height", 1080))
        self.fps = video_cfg.get("fps", 30)
        self.preset = video_cfg.get("preset", "veryfast")
        self.crf = video_cfg.get("crf", 23)
        self.ffmpeg_path = "ffmpeg"

        cache_dir = config.get("paths", {}).get("cache", "./cache")
        self.temp_dir = Path(cache_dir) / "render_temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self._config = config

    def render(
        self,
        timeline: Timeline,
        output_path: str,
        assets_dir: str = "./assets",
        bgm_file: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
        cancel_event: Optional[threading.Event] = None,
        style: Optional[str] = None,
    ) -> str:
        if not check_ffmpeg():
            raise RuntimeError("FFmpeg 未安装或未加入 PATH")

        total_duration = timeline.timeline[-1].end if timeline.timeline else 0
        if total_duration <= 0:
            raise ValueError("Timeline 总时长为 0")

        voice_entries = sum(1 for item in timeline.timeline
                            if hasattr(item, 'voice_file') and item.voice_file)
        if voice_entries > 60:
            raise RuntimeError(
                f"配音段落数 {voice_entries} 超过上限（60 段），"
                f"FFmpeg amix 滤镜最多同时处理 64 路音频。"
                f"请合并短段落后重试。"
            )
        if total_duration > 3600:
            raise ValueError(
                f"视频总时长 {total_duration:.0f}s 超过上限 3600 秒（1 小时）。"
            )

        self._report(progress_callback, 0.0, "准备渲染...")
        self._cancel_event = cancel_event

        def _check_cancel():
            if self._cancel_event and self._cancel_event.is_set():
                raise RuntimeError("用户取消")

        temp_workspace = Path(tempfile.mkdtemp(dir=str(self.temp_dir)))
        try:
            log.info("开始渲染: %s", output_path)
            clip_files = self._render_clips(timeline, assets_dir, str(temp_workspace),
                                            total_duration, progress_callback, style)
            if not clip_files:
                raise RuntimeError("没有成功渲染的镜头")
            log.info("镜头渲染完成: %d 个", len(clip_files))
            _check_cancel()

            concat_path = str(temp_workspace / "_concat.mp4")
            transitions = [item.transition for item in timeline.timeline]
            valid_trans = transitions[:-1] if len(transitions) > 1 else []
            has_transitions = any(t != "cut" for t in valid_trans)
            clips_have_audio = any(self._has_audio_stream(p) for p in clip_files)
            if has_transitions and len(clip_files) > 1 and clips_have_audio:
                xfade_list = valid_trans
                success, err = concat_with_xfade(
                    clip_files, concat_path, xfade_list, self.ffmpeg_path,
                    trans_duration=0.5,
                )
                if not success:
                    log.warning("xfade 拼接失败, 回退到 concat: %s", err)
                    success, err = self._concat_video_only(clip_files, concat_path)
            else:
                success, err = self._concat_video_only(clip_files, concat_path)
            if not success:
                log.error("拼接失败: %s", err)
                raise RuntimeError(f"视频拼接失败: {err}")
            concat_dur = self._get_clip_duration(concat_path)
            concat_frames = self._get_clip_frames(concat_path)
            log.info("视频拼接完成: 期望=%.1fs/%d 实际=%.1fs/%d 帧",
                     total_duration, int(total_duration * self.fps), concat_dur, concat_frames)
            _check_cancel()

            # ── separate audio processing ──
            has_voice = any(item.voice_file for item in timeline.timeline)
            audio_path: Optional[str] = None
            bgm_volume = self._config.get("bgm", {}).get("volume", 0.3)

            if has_voice or (bgm_file and os.path.exists(bgm_file)):
                self._report(progress_callback, 0.82, "合成完整音轨...")
                log.info("生成配音轨...")
                narration_path = str(temp_workspace / "_narration.wav")
                if has_voice:
                    narration_path = self._build_narration_track(timeline, narration_path)
                if narration_path:
                    audio_path = narration_path
                _check_cancel()

            if bgm_file and os.path.exists(bgm_file) and audio_path:
                self._report(progress_callback, 0.88, "混合 BGM...")
                log.info("混合 BGM...")
                mixed_path = str(temp_workspace / "_voice_bgm.wav")
                audio_path = self._mix_bgm_audio(audio_path, bgm_file, total_duration, mixed_path)
                _check_cancel()

            if audio_path:
                self._report(progress_callback, 0.91, "音量归一化...")
                log.info("音量归一化...")
                norm_path = str(temp_workspace / "_norm_audio.wav")
                cmd = [
                    self.ffmpeg_path, "-y", "-i", audio_path,
                    "-filter:a", "loudnorm",
                    "-c:a", "pcm_s16le",
                    norm_path,
                ]
                ok, _ = execute(cmd, cancel_event=getattr(self, '_cancel_event', None))
                if ok:
                    audio_path = norm_path
                    log.info("音量归一化完成")
                else:
                    log.warning("loudnorm 失败, 跳过")

            # ── mux video + audio ──
            if audio_path and os.path.exists(audio_path):
                self._report(progress_callback, 0.93, "合成音视频...")
                muxed_path = str(temp_workspace / "_muxed.mp4")
                final_path = self._mux_video_audio(concat_path, audio_path, muxed_path, total_duration)
                if final_path == muxed_path:
                    mux_frames = self._get_clip_frames(final_path)
                    log.info("音视频合成完成: %d 帧", mux_frames)
            else:
                final_path = concat_path

            # Step: hardcode subtitles (libass ass filter or Pillow PNG overlay)
            has_subtitle = any(item.subtitle for item in timeline.timeline)
            if has_subtitle:
                self._report(progress_callback, 0.95, "叠加字幕...")
                subtitle_ass = str(temp_workspace / "_subtitle.ass")
                self._generate_subtitle_file(timeline, subtitle_ass)
                use_libass = Renderer._has_libass_working
                if use_libass is None:
                    use_libass = has_libass()
                if use_libass:
                    ass_out = str(temp_workspace / "_with_sub_ass.mp4")
                    log.info("使用 libass 叠加字幕...")
                    ass_path = self._burn_subtitle_ass(final_path, subtitle_ass, ass_out)
                    if ass_path != final_path:
                        final_path = ass_path
                        Renderer._has_libass_working = True
                    else:
                        Renderer._has_libass_working = False
                        log.info("libass 回退到 Pillow 叠加")
                        final_path = self._hardcode_subtitle(final_path, subtitle_ass, total_duration,
                                                              str(temp_workspace / "_with_sub_pillow.mp4"))
                else:
                    log.info("使用 Pillow 叠加字幕")
                    final_path = self._hardcode_subtitle(final_path, subtitle_ass, total_duration,
                                                          str(temp_workspace / "_with_sub.mp4"))
                log.info("字幕叠加完成")

            final_frames = self._get_clip_frames(final_path)
            log.info("最终输出: %d 帧 %.1fs", final_frames, self._get_clip_duration(final_path))

            tmp = output_path + ".tmp"
            try:
                shutil.copy2(final_path, tmp)
                os.replace(tmp, output_path)
            except OSError:
                log.warning("输出文件被占用，使用唯一文件名")
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                base, ext = os.path.splitext(output_path)
                import time
                output_path = f"{base}_{int(time.time())}{ext}"
                shutil.copy2(final_path, output_path)
            self._report(progress_callback, 1.0, "渲染完成")
            log.info("渲染完成: %s", output_path)
            return output_path
        except Exception:
            log.error("渲染异常:\n%s", traceback.format_exc())
            raise
        finally:
            shutil.rmtree(str(temp_workspace), ignore_errors=True)

    def _render_clips(
        self,
        timeline: Timeline,
        assets_dir: str,
        workspace: str,
        total_duration: float,
        progress_callback: Optional[Callable[[float], None]] = None,
        style: Optional[str] = None,
    ) -> list[str]:
        clip_files: list[str] = []
        w, h = self.resolution

        for i, item in enumerate(timeline.timeline):
            item_duration = item.end - item.start
            out_path = os.path.join(workspace, f"clip_{i:04d}.mp4")

            asset_path = self._find_asset(item.asset, assets_dir, item.asset_type)
            log.info("镜头 %d: asset=%s type=%s path=%s found=%s",
                     i, item.asset, item.asset_type,
                     asset_path or "N/A", bool(asset_path))
            ok = False
            if asset_path and os.path.exists(asset_path):
                ok = self._render_clip_with_asset(asset_path, item_duration, out_path, w, h, item.camera, style)
                if not ok:
                    log.warning("镜头 %d: 素材渲染失败 %s，回退到占位符", i, asset_path)
            if not ok:
                ok = self._render_clip_placeholder(item, item_duration, out_path, w, h)
            if not ok:
                log.warning("镜头 %d 渲染失败，跳过", i)
                continue

            clip_files.append(out_path)
            real_dur = self._get_clip_duration(out_path)
            fsize = os.path.getsize(out_path)
            fcount = self._get_clip_frames(out_path)
            log.info("镜头 %d: 时长=%.2fs 帧数=%d 大小=%d (期望 %.0fs/%dframes)",
                     i, real_dur, fcount, fsize, item_duration, int(item_duration * self.fps))
            if real_dur < 0.1 or fsize < 10000:
                log.error("镜头 %d: 片段异常（时长=%.2fs 大小=%d），跳过", i, real_dur, fsize)
                clip_files.pop()

            if progress_callback:
                progress = ((i + 1) / len(timeline.timeline)) * 0.8
                progress_callback(progress)

        return clip_files

    def _build_camera_filter(self, camera: str, w: int, h: int) -> str:
        base = f"scale={w}:{h}:force_original_aspect_ratio=decrease"
        if camera == "slow_zoom":
            return f"{base},zoompan=z='min(zoom+0.0015,1.5)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={self.fps}"
        elif camera == "pan":
            return f"{base},crop={w}:{h}:'min((iw-{w})*t/{self.fps},{iw-w})':0"
        else:
            return f"{base},pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"

    def _render_clip_with_asset(self, asset_path: str, duration: float, out_path: str, w: int, h: int,
                                 camera: str = "static", style: Optional[str] = None) -> bool:
        vf = self._build_camera_filter(camera, w, h)
        grade = COLOR_PRESETS.get(style or "", "")
        if grade:
            vf = f"{vf},{grade}"
        vf_full = f"fps={self.fps},{vf},format=yuv420p,setsar=1"
        is_image = asset_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".webp"))
        cmd = [self.ffmpeg_path, "-y"]
        if is_image:
            cmd.extend(["-loop", "1"])
        cmd.extend([
            "-i", asset_path,
            "-c:v", "libx264", "-preset", self.preset, "-crf", str(self.crf),
            "-r", str(self.fps), "-g", "60", "-keyint_min", "60", "-sc_threshold", "0",
            "-vf", vf_full,
            "-an",
            "-vsync", "cfr", "-t", str(duration),
            "-video_track_timescale", str(self.fps * 1000),
            "-movflags", "+faststart",
            out_path,
        ])
        success, err = execute(cmd, timeout=300, cancel_event=getattr(self, '_cancel_event', None))
        if not success:
            self._log_execute_error(cmd, err)
        return success

    def _render_clip_placeholder(self, item: TimelineItem, duration: float, out_path: str, w: int, h: int) -> bool:
        color_map = {
            "normal": "blue", "big_yellow": "gold", "bold": "red",
            "soft_white": "gray", "calm": "lightblue", "strong": "gold",
            "happy": "red", "sad": "gray", "knowledge": "steelblue",
            "news": "white", "entertainment": "green", "commerce": "gold",
            "scifi": "cyan", "tech": "limegreen", "custom": "blue",
        }
        color = color_map.get(item.subtitle_style, "blue")
        vf_full = f"fps={self.fps},scale={w}:{h},format=yuv420p,setsar=1"
        cmd = [
            self.ffmpeg_path, "-y",
            "-f", "lavfi", "-i", f"color=c={color}:s={w}x{h}:r={self.fps}:d={duration}",
            "-c:v", "libx264", "-preset", self.preset, "-crf", str(self.crf),
            "-r", str(self.fps), "-g", "60", "-keyint_min", "60", "-sc_threshold", "0",
            "-vf", vf_full,
            "-an",
            "-vsync", "cfr", "-t", str(duration),
            "-video_track_timescale", str(self.fps * 1000),
            "-movflags", "+faststart",
            out_path,
        ]
        try:
            success, err = execute(cmd, timeout=60, cancel_event=getattr(self, '_cancel_event', None))
            if not success:
                self._log_execute_error(cmd, err)
                return False
            return True
        except Exception as e:
            log.warning("占位镜头渲染异常: %s", e)
            return False

    # ── hardcode subtitles via Pillow PNG overlay ──────────────────────

    def _hardcode_subtitle(self, video_path: str, ass_path: str, total_duration: float, out_path: str) -> str:
        if not _HAS_PILLOW:
            log.warning("Pillow not installed; skipping subtitle overlay")
            shutil.copy2(video_path, out_path)
            return out_path

        events = self._parse_ass_events(ass_path)
        if not events:
            shutil.copy2(video_path, out_path)
            return out_path

        w, h = self.resolution
        png_dir = Path(ass_path).parent / "_sub_pngs"
        png_dir.mkdir(parents=True, exist_ok=True)

        png_files = []
        for idx, (start, end, text, style_name) in enumerate(events):
            png_path = str(png_dir / f"sub_{idx:04d}.png")
            self._render_subtitle_png(text, style_name, w, h, png_path)
            png_files.append((start, end, png_path))

        # Build overlay filter chain: each PNG is a separate input + overlay with enable
        inputs = [video_path]
        filter_chains = []
        for idx, (start, end, png_path) in enumerate(png_files):
            inputs.append(png_path)
            input_idx = idx + 1
            prev = f"[v{idx}]" if idx > 0 else "[0:v]"
            next_label = f"v{idx + 1}"
            filter_chains.append(
                f"{prev}[{input_idx}:v]overlay=0:0:enable='between(t,{start},{end})'[{next_label}]"
            )

        filter_complex = ";".join(filter_chains)
        last_label = f"[v{len(png_files)}]"

        cmd = (
            FFmpegBuilder()
        )
        for idx, inp in enumerate(inputs):
            if idx == 0:
                cmd.input(inp)
            else:
                cmd.input(inp, {"loop": "-1"})
        cmd = cmd.filter_complex(filter_complex)
        cmd = cmd.output(out_path, {
            "map": [last_label, "0:a?"],
            "c:v": "libx264", "preset": self.preset, "crf": str(self.crf),
            "pix_fmt": "yuv420p", "r": str(self.fps),
            "video_track_timescale": str(self.fps * 1000),
            "movflags": "+faststart",
            "c:a": "copy",
        })
        raw_cmd = cmd.build()

        try:
            success, err = execute(raw_cmd, timeout=120, cancel_event=getattr(self, '_cancel_event', None))
            if success and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                return out_path
            log.warning("Pillow 字幕叠加失败: %s", err[:200] if err else f"rc={raw_cmd}")
            shutil.copy2(video_path, out_path)
            return out_path
        except Exception as e:
            log.warning("Pillow 字幕叠加异常: %s", e)
            shutil.copy2(video_path, out_path)
            return out_path

    def _render_subtitle_png(self, text: str, style_name: str, w: int, h: int, out_path: str):
        style_fonts = {
            "normal":     ("msyh.ttc", 40, (255, 255, 255)),
            "big_yellow": ("msyhbd.ttc", 52, (255, 215, 0)),
            "soft_white": ("msyh.ttc", 40, (224, 224, 224)),
            "bold":       ("msyhbd.ttc", 44, (255, 107, 107)),
        }
        font_name, font_size, color = style_fonts.get(style_name, style_fonts["normal"])
        outline = (0, 0, 0, 200)

        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype(font_name, font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

        lines = text.split("\n")
        line_h = font_size + 8
        total_h = len(lines) * line_h
        y_start = h - total_h - 60

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            x = (w - tw) // 2

            for dx, dy in [(-3, -1), (3, -1), (-3, 1), (3, 1)]:
                draw.text((x + dx, y_start + dy), line, font=font, fill=outline)
            draw.text((x, y_start), line, font=font, fill=color + (255,))
            y_start += line_h

        img.save(out_path, "PNG")

    def _parse_ass_events(self, ass_path: str) -> list[tuple[float, float, str, str]]:
        if not os.path.exists(ass_path):
            return []
        with open(ass_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Determine style name from the ASS header
        style_match = re.search(r"^Style:\s*(\w+)", content, re.MULTILINE)
        ass_style_name = style_match.group(1) if style_match else "Default"

        events = re.findall(
            r"^Dialogue:\s*\d+,(\d+:\d+:\d+[.,]\d+),(\d+:\d+:\d+[.,]\d+),[^,]*,[^,]*,(\d+),(\d+),(\d+),,(.+)",
            content,
            re.MULTILINE,
        )
        result = []
        for s_start, s_end, _, _, _, s_text in events:
            start = self._parse_ass_time(s_start)
            end = self._parse_ass_time(s_end)
            text = s_text.replace("\\N", "\n").strip()
            if text:
                result.append((start, end, text, ass_style_name))
        return result

    @staticmethod
    def _parse_ass_time(t: str) -> float:
        parts = t.replace(",", ".").split(":")
        h = int(parts[0])
        m = int(parts[1])
        s = float(parts[2])
        return h * 3600 + m * 60 + s

    @staticmethod
    def _escape_filter_path(path: str) -> str:
        s = str(Path(path).resolve().as_posix())
        if len(s) >= 2 and s[1] == ":":
            s = s[2:]
        s = s.replace(",", "\\,")
        s = s.replace("'", "\\'")
        return s

    def _burn_subtitle_ass(self, video_path: str, ass_path: str, out_path: str) -> str:
        ass_path_no_drive = self._escape_filter_path(ass_path)
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", video_path,
            "-vf", f"subtitles={ass_path_no_drive}",
            "-c:a", "copy",
            "-c:v", "libx264", "-preset", self.preset, "-crf", str(self.crf),
            "-pix_fmt", "yuv420p", "-r", str(self.fps), "-vsync", "cfr",
            "-video_track_timescale", str(self.fps * 1000),
            "-movflags", "+faststart",
            out_path,
        ]
        try:
            success, err = execute(cmd, timeout=30, cancel_event=getattr(self, '_cancel_event', None))
            if success and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                return out_path
            self._log_execute_error(cmd, err)
        except Exception as e:
            log.warning("ass 滤镜异常: %s", e)
        return video_path

    # ── video-only concat ─────────────────────────────────────────────

    def _concat_video_only(self, clip_files: list[str], out_path: str) -> tuple[bool, str]:
        filelist = "\n".join(f"file '{p}'" for p in clip_files)
        filelist_path = os.path.join(os.path.dirname(out_path), "_concat_list.txt")
        with open(filelist_path, "w", encoding="utf-8") as f:
            f.write(filelist)
        cmd = [
            self.ffmpeg_path, "-y",
            "-f", "concat", "-safe", "0",
            "-fflags", "+genpts",
            "-i", filelist_path,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-vsync", "cfr",
            "-an",
            "-video_track_timescale", "30000",
            "-movflags", "+faststart",
            out_path,
        ]
        result = execute(cmd)
        try:
            os.unlink(filelist_path)
        except OSError:
            pass
        return result

    # ── separate audio pipeline ───────────────────────────────────────

    def _build_narration_track(self, timeline: Timeline, out_path: str) -> str:
        voice_entries = [
            (item.start, item.end - item.start, item.voice_file)
            for item in timeline.timeline
            if item.voice_file and os.path.exists(item.voice_file)
        ]
        if not voice_entries:
            return ""

        n = len(voice_entries)
        filter_parts = []
        for i, (start, duration, vf) in enumerate(voice_entries):
            delay_ms = int(start * 1000)
            filter_parts.append(f"[{i}:a]atrim=end={duration}[t{i}];[t{i}]adelay={delay_ms}:all=1[d{i}]")

        mix_inputs = "".join(f"[d{i}]" for i in range(n))
        filter_parts.append(f"{mix_inputs}amix=inputs={n}[a]")
        filter_complex = ";".join(filter_parts)

        cmd = [self.ffmpeg_path, "-y"]
        for _, _, vf in voice_entries:
            cmd.extend(["-i", vf])
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[a]",
            "-c:a", "pcm_s16le",
            out_path,
        ])
        success, err = execute(cmd, cancel_event=getattr(self, '_cancel_event', None))
        if not success:
            self._log_execute_error(cmd, err)
            return ""
        return out_path

    def _mix_bgm_audio(self, voice_path: str, bgm_path: str, total_duration: float, out_path: str) -> str:
        bgm_volume = self._config.get("bgm", {}).get("volume", 0.3)
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", voice_path,
            "-i", bgm_path,
            "-filter_complex",
            f"[1:a]volume={bgm_volume}[bgm];"
            f"[0:a]asplit=2[voice][sidechain];"
            f"[bgm][sidechain]sidechaincompress=threshold=-34dB:ratio=12:attack=0.002:release=0.5[bgm_ducked];"
            f"[voice][bgm_ducked]amix=inputs=2:duration=longest[a]",
            "-map", "[a]",
            "-c:a", "pcm_s16le",
            out_path,
        ]
        success, err = execute(cmd, cancel_event=getattr(self, '_cancel_event', None))
        if not success:
            self._log_execute_error(cmd, err)
            return voice_path
        return out_path

    def _mux_video_audio(self, video_path: str, audio_path: str, out_path: str, total_duration: float) -> str:
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
            "-map", "0:v", "-map", "1:a",
            "-shortest",
            out_path,
        ]
        success, err = execute(cmd, cancel_event=getattr(self, '_cancel_event', None))
        if not success:
            self._log_execute_error(cmd, err)
            return video_path
        return out_path

    def _has_audio_stream(self, video_path: str) -> bool:
        try:
            r = subprocess.run(
                [self.ffmpeg_path, "-i", video_path],
                capture_output=True, timeout=15,
            )
            return "Audio:" in _decode_ffmpeg(r.stderr)
        except Exception:
            return False

    def _generate_subtitle_file(self, timeline: Timeline, output_path: str):
        from core.subtitle import SubtitleGenerator
        gen = SubtitleGenerator(self._config)
        segments = [(item.start, item.end, item.subtitle, item.subtitle_style, item.subtitle_animation)
                     for item in timeline.timeline if item.subtitle]
        gen.generate_from_text(segments, output_path)

    def _find_asset(self, filename: str, assets_dir: str, asset_type: str) -> Optional[str]:
        if not filename:
            return None
        subdirs = {"video": "videos", "image": "images", "bgm": "bgm", "voice": "voice"}
        subdir = subdirs.get(asset_type, "videos")
        type_dir = os.path.join(assets_dir, subdir)
        path = os.path.join(type_dir, filename)
        if os.path.exists(path):
            return path
        if os.path.isdir(type_dir):
            for root, _dirs, files in os.walk(type_dir):
                if filename in files:
                    return os.path.join(root, filename)
        for root, _dirs, files in os.walk(assets_dir):
            if filename in files:
                return os.path.join(root, filename)
        return None

    def _report(self, callback: Optional[Callable], progress: float, message: str = ""):
        if callback:
            callback(progress)

    @staticmethod
    def _log_execute_error(cmd: list[str], err: str):
        log.warning("FFmpeg 命令失败:\n  CMD: %s\n  ERR: %s", " ".join(cmd), err[:2000])

    def _get_clip_duration(self, path: str) -> float:
        return get_clip_duration(path, self.ffmpeg_path)

    def _get_clip_frames(self, path: str) -> int:
        try:
            p = Path(self.ffmpeg_path)
            ffprobe = str(p.with_name(p.name.replace("ffmpeg", "ffprobe")))
            r = subprocess.run(
                [ffprobe, "-v", "error", "-count_frames",
                 "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames",
                 "-of", "csv=p=0", path],
                capture_output=True, timeout=15,
            )
            out = _decode_ffmpeg(r.stdout).strip()
            return int(out) if out else 0
        except Exception:
            return 0
