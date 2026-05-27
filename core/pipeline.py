import json
import os
import shutil
import subprocess
import threading
import logging
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum

from core.config import get_config, get
from core.database import Database
from core.scanner import AssetScanner
from core.matcher import Matcher
from core.rules import RuleEngine
from core.timeline import TimelineBuilder, TimelineValidator
from core.tts import TTSModule
from core.subtitle import SubtitleGenerator
from core.renderer import Renderer
from core.models import Script


class PipelineStep(Enum):
    INIT = "init"
    LOAD_SCRIPT = "load_script"
    MATCH_ASSETS = "match_assets"
    APPLY_RULES = "apply_rules"
    BUILD_TIMELINE = "build_timeline"
    GENERATE_TTS = "generate_tts"
    GENERATE_SUBTITLE = "generate_subtitle"
    RENDER_VIDEO = "render_video"
    DONE = "done"


@dataclass
class PipelineProgress:
    step: PipelineStep
    progress: float
    message: str


class PipelineError(Exception):
    def __init__(self, step: PipelineStep, message: str, cause: Optional[Exception] = None):
        self.step = step
        self.cause = cause
        super().__init__(f"[{step.value}] {message}")


class Pipeline:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or get_config()

        log_level = self.config.get("logging", {}).get("level", "INFO")
        logging.basicConfig(level=getattr(logging, log_level))

        self.logger = logging.getLogger("pipeline")
        self._cancelled = False
        self._cancel_event = threading.Event()

    def run(
        self,
        script_path: str,
        output_path: str,
        progress_callback: Optional[Callable[[PipelineProgress], None]] = None,
    ) -> str:
        self._cancelled = False
        db = Database(get("paths.database", "./database/clipforge.db"))
        db.init_tables()

        matcher = Matcher(db)
        rule_engine = RuleEngine()
        rule_engine.register_defaults()
        timeline_builder = TimelineBuilder(matcher, rule_engine)
        tts_module = TTSModule(self.config)
        subtitle_gen = SubtitleGenerator(self.config)
        renderer = Renderer(self.config)

        assets_dir = get("paths.assets", "./assets")

        voice_dir = None
        subtitle_path = None

        try:
            self._report(progress_callback, PipelineStep.INIT, 0.0, "初始化...")

            self._report(progress_callback, PipelineStep.LOAD_SCRIPT, 0.0, "加载脚本...")
            with open(script_path, "r", encoding="utf-8") as f:
                script_data = json.load(f)
            script = Script(**script_data)
            self.logger.info(f"脚本加载成功: {script.title} ({len(script.segments)} 分段)")

            if self._cancelled:
                raise PipelineError(PipelineStep.LOAD_SCRIPT, "用户取消")

            self._report(progress_callback, PipelineStep.MATCH_ASSETS, 0.0, "匹配素材...")
            total_segments = len(script.segments)
            for i, seg in enumerate(script.segments):
                assets = matcher.match(seg.text, seg.keywords, top_k=3)
                if assets:
                    self.logger.info(f"  分段 {seg.id}: 匹配到 {len(assets)} 个素材")
                else:
                    self.logger.warning(f"  分段 {seg.id}: 未匹配到素材，将使用占位符")
                if progress_callback:
                    progress_callback(PipelineProgress(
                        PipelineStep.MATCH_ASSETS,
                        (i + 1) / total_segments,
                        f"匹配素材 {i+1}/{total_segments}",
                    ))

            if self._cancelled:
                raise PipelineError(PipelineStep.MATCH_ASSETS, "用户取消")

            self._report(progress_callback, PipelineStep.APPLY_RULES, 0.5, "应用规则...")

            self._report(progress_callback, PipelineStep.BUILD_TIMELINE, 0.0, "构建时间轴...")
            timeline = timeline_builder.build(script)
            validator = TimelineValidator()
            errors = validator.validate(timeline)
            if errors:
                self.logger.warning(f"Timeline 校验警告: {errors}")
            self.logger.info(f"Timeline 构建完成: {len(timeline.timeline)} 个镜头, 总时长 {timeline.timeline[-1].end:.1f}s")

            if self._cancelled:
                raise PipelineError(PipelineStep.BUILD_TIMELINE, "用户取消")

            self._report(progress_callback, PipelineStep.GENERATE_TTS, 0.0, "生成配音...")
            voice_dir = os.path.join(os.path.dirname(output_path), "_temp_voice")
            voice_segments = [(seg.id, seg.text) for seg in script.segments]
            tts_module.generate_batch(voice_segments, voice_dir)
            voice_files = sorted(
                [os.path.join(voice_dir, f) for f in os.listdir(voice_dir) if f.endswith(".wav")],
                key=lambda x: int(os.path.basename(x).replace("voice_", "").replace(".wav", ""))
            )
            for item, vf in zip(timeline.timeline, voice_files):
                item.voice_file = vf
            self.logger.info(f"配音生成完成: {len(voice_files)} 个文件")

            def _is_silent_audio(path: str) -> bool:
                try:
                    r = subprocess.run(
                        ["ffmpeg", "-v", "info", "-i", path,
                         "-af", "volumedetect", "-t", "2.0",
                         "-f", "null", "-"],
                        capture_output=True, timeout=10,
                    )
                    err = r.stderr.decode(errors="replace")
                    return "mean_volume: -inf" in err
                except Exception:
                    return not os.path.exists(path) or os.path.getsize(path) < 5000

            if not voice_files or all(_is_silent_audio(f) for f in voice_files if os.path.exists(f)):
                self.logger.warning("TTS 生成文件为空或静音，尝试使用素材库中的 voice 文件")
                voice_assets = db.search_assets(type_filter="voice", limit=50)
                if voice_assets:
                    for idx, item in enumerate(timeline.timeline):
                        seg_keywords = self._get_item_keywords(idx, script)
                        if seg_keywords:
                            best = self._best_voice_match(voice_assets, seg_keywords, assets_dir)
                            if best:
                                item.voice_file = best
                    used = sum(1 for item in timeline.timeline if item.voice_file)
                    self.logger.info(f"使用素材库 voice 文件: {used} 个镜头")

            if self._cancelled:
                raise PipelineError(PipelineStep.GENERATE_TTS, "用户取消")

            self._report(progress_callback, PipelineStep.GENERATE_SUBTITLE, 0.0, "生成字幕...")
            subtitle_path = os.path.join(os.path.dirname(output_path), "_temp_subtitle.ass")
            subtitle_segments = [(item.start, item.end, item.subtitle, item.subtitle_style)
                                  for item in timeline.timeline if item.subtitle]
            subtitle_gen.generate_from_text(subtitle_segments, subtitle_path)
            self.logger.info(f"字幕生成完成: {subtitle_path}")

            if self._cancelled:
                raise PipelineError(PipelineStep.GENERATE_SUBTITLE, "用户取消")

            self._report(progress_callback, PipelineStep.RENDER_VIDEO, 0.0, "渲染视频...")
            def render_progress(pct: float):
                if progress_callback:
                    progress_callback(PipelineProgress(PipelineStep.RENDER_VIDEO, pct, f"渲染中 {pct*100:.0f}%"))
                if self._cancelled:
                    raise PipelineError(PipelineStep.RENDER_VIDEO, "用户取消")

            bgm_path = None
            bgm_dir = os.path.join(assets_dir, "bgm")
            if script.bgm:
                bgm_path = os.path.join(bgm_dir, script.bgm)
                if not os.path.exists(bgm_path) and os.path.isdir(bgm_dir):
                    for root, _dirs, files in os.walk(bgm_dir):
                        if script.bgm in files:
                            bgm_path = os.path.join(root, script.bgm)
                            break
                    else:
                        bgm_path = None
            if not bgm_path:
                bgm_matches = matcher.match_bgm(style=script.style, top_k=1)
                if bgm_matches:
                    bgm_path = os.path.join(bgm_dir, bgm_matches[0].file)
                    if not os.path.exists(bgm_path) and os.path.isdir(bgm_dir):
                        for root, _dirs, files in os.walk(bgm_dir):
                            if bgm_matches[0].file in files:
                                bgm_path = os.path.join(root, bgm_matches[0].file)
                                break
                        else:
                            bgm_path = None
                if not bgm_path:
                    all_bgm = db.search_assets(type_filter="bgm", limit=1)
                    if all_bgm and os.path.isdir(bgm_dir):
                        for root, _dirs, files in os.walk(bgm_dir):
                            if all_bgm[0].file in files:
                                bgm_path = os.path.join(root, all_bgm[0].file)
                                break

            result_path = renderer.render(
                timeline=timeline,
                output_path=output_path,
                assets_dir=assets_dir,
                bgm_file=bgm_path,
                progress_callback=render_progress,
                cancel_event=self._cancel_event,
            )
            self.logger.info(f"渲染完成: {result_path}")

            if os.path.exists(voice_dir):
                shutil.rmtree(voice_dir, ignore_errors=True)
            if os.path.exists(subtitle_path):
                os.unlink(subtitle_path)

            self._report(progress_callback, PipelineStep.DONE, 1.0, "完成!")
            return result_path

        except PipelineError:
            self._cleanup_temp(voice_dir, subtitle_path)
            raise
        except json.JSONDecodeError as e:
            self._cleanup_temp(voice_dir, subtitle_path)
            raise PipelineError(PipelineStep.LOAD_SCRIPT, f"脚本 JSON 格式错误: {e}", e)
        except Exception as e:
            self._cleanup_temp(voice_dir, subtitle_path)
            raise PipelineError(PipelineStep.RENDER_VIDEO, f"处理失败: {e}", e)
        finally:
            db.close()

    def _cleanup_temp(self, voice_dir, subtitle_path):
        if voice_dir and os.path.exists(voice_dir):
            shutil.rmtree(voice_dir, ignore_errors=True)
        if subtitle_path and os.path.exists(subtitle_path):
            try:
                os.unlink(subtitle_path)
            except OSError:
                pass

    def run_batch(
        self,
        script_paths: list[str],
        output_dir: str,
        progress_callback: Optional[Callable[[PipelineProgress], None]] = None,
    ) -> list[tuple[str, bool, str]]:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        results: list[tuple[str, bool, str]] = []

        for i, script_path in enumerate(script_paths):
            script_name = Path(script_path).stem
            output_path = os.path.join(output_dir, f"{script_name}.mp4")

            self._report(progress_callback, PipelineStep.INIT, i / len(script_paths),
                         f"[{i+1}/{len(script_paths)}] {script_name}")

            try:
                result = self.run(script_path, output_path)
                results.append((script_path, True, result))
            except PipelineError as e:
                self.logger.error(f"处理失败 {script_path}: {e}")
                results.append((script_path, False, str(e)))

        return results

    def _get_item_keywords(self, item_idx: int, script) -> list[str]:
        if 0 <= item_idx < len(script.segments):
            return script.segments[item_idx].keywords
        return []

    def _best_voice_match(self, voice_assets, keywords: list[str], assets_dir: str) -> Optional[str]:
        if not keywords or not voice_assets:
            return None
        best_score = 0.0
        best_path = None
        for asset in voice_assets:
            path = os.path.join(assets_dir, "voice", asset.file)
            if not os.path.exists(path):
                continue
            score = sum(2.0 for kw in keywords if kw in asset.tags)
            if score > best_score:
                best_score = score
                best_path = path
        return best_path

    def validate_script(self, script_path: str) -> list[str]:
        errors: list[str] = []
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            Script(**data)
        except json.JSONDecodeError as e:
            errors.append(f"JSON 格式错误: {e}")
        except Exception as e:
            errors.append(str(e))
        return errors

    def cancel(self):
        self._cancelled = True
        self._cancel_event.set()

    def _report(
        self,
        callback: Optional[Callable[[PipelineProgress], None]],
        step: PipelineStep,
        progress: float,
        message: str,
    ):
        if callback:
            callback(PipelineProgress(step=step, progress=progress, message=message))
