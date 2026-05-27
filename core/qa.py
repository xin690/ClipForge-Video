"""QA 质检模块

对 Script 进行全面质量检查，返回结构化检查结果。
支持根据导出预设调整检查阈值。
"""

from dataclasses import dataclass, field
from typing import Literal, Optional
from core.models import Script, Segment
from core.config import get_config

CheckStatus = Literal["pass", "warn", "fail"]

_VALID_STYLES = {"knowledge", "news", "entertainment", "commerce"}
_VALID_EMOTIONS = {"normal", "strong", "happy", "sad", "calm"}
_VALID_VOICES = {
    "zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural",
    "zh-CN-XiaoyiNeural", "zh-CN-YunyangNeural",
    "zh-CN-YunjianNeural",
}
_EMOTION_TRANSITIONS = {
    "normal": {"strong", "happy", "sad", "calm"},
    "strong": {"normal", "happy", "sad", "calm"},
    "happy": {"normal", "strong", "sad", "calm"},
    "sad": {"normal", "strong", "happy", "calm"},
    "calm": {"normal", "strong", "happy", "sad"},
}


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    message: str
    segment_id: Optional[int] = None


@dataclass
class QASummary:
    total: int = 0
    passed: int = 0
    warnings: int = 0
    failures: int = 0
    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed_all(self) -> bool:
        return self.failures == 0


class QAChecker:
    """质检引擎。"""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or get_config()
        self.preset = (self.config.get("qa", {})).get("preset", "tiktok")

        _presets = (self.config.get("qa", {})).get("presets", {})
        self.thresholds = _presets.get(self.preset, _presets.get("tiktok", {}))
        self.segment_min = self.thresholds.get("segment_min", 3)
        self.segment_max = self.thresholds.get("segment_max", 10)
        self.duration_per_seg_min = self.thresholds.get("duration_per_seg_min", 2)
        self.duration_per_seg_max = self.thresholds.get("duration_per_seg_max", 10)
        self.total_duration_max = self.thresholds.get("total_duration_max", 600)
        self.text_min_len = self.thresholds.get("text_min_len", 10)
        self.text_max_len = self.thresholds.get("text_max_len", 200)
        self.min_keywords = self.thresholds.get("min_keywords", 2)
        self.duration_tolerance = self.thresholds.get("duration_tolerance", 5)

    def check(self, script: Script) -> QASummary:
        results: list[CheckResult] = []

        results.append(self._check_segment_count(script))
        for seg in script.segments:
            results.extend(self._check_segment(script, seg))
        results.extend(self._check_emotion_sequence(script))
        results.extend(self._check_keyword_diversity(script))
        results.append(self._check_voice(script))
        results.append(self._check_style(script))
        results.append(self._check_bgm(script))
        results.append(self._check_total_duration_match(script))

        non_none = [r for r in results if r is not None]
        summary = QASummary(results=non_none)
        summary.total = len(non_none)
        for r in non_none:
            if r.status == "pass":
                summary.passed += 1
            elif r.status == "warn":
                summary.warnings += 1
            elif r.status == "fail":
                summary.failures += 1
        return summary

    def _check_segment_count(self, script: Script) -> CheckResult:
        n = len(script.segments)
        if n < self.segment_min:
            return CheckResult(
                "segment_count", "fail",
                f"分段数 {n} 少于最小值 {self.segment_min}",
            )
        if n > self.segment_max:
            return CheckResult(
                "segment_count", "warn",
                f"分段数 {n} 超过建议值 {self.segment_max}，可能导致剪辑节奏松散",
            )
        return CheckResult("segment_count", "pass", f"{n} 个分段，数量合理")

    def _check_segment(self, script: Script, seg: Segment) -> list[CheckResult]:
        results = []
        results.append(self._check_duration(seg))
        results.append(self._check_text_length(seg))
        results.append(self._check_keywords(seg))
        results.append(self._check_emotion(seg))
        return results

    def _check_duration(self, seg: Segment) -> CheckResult:
        if seg.duration < self.duration_per_seg_min:
            return CheckResult(
                "segment_duration", "warn",
                f"段{seg.id} 时长 {seg.duration}s 过短（建议 {self.duration_per_seg_min}~{self.duration_per_seg_max}s）",
                seg.id,
            )
        if seg.duration > self.duration_per_seg_max:
            return CheckResult(
                "segment_duration", "warn",
                f"段{seg.id} 时长 {seg.duration}s 过长（建议 {self.duration_per_seg_min}~{self.duration_per_seg_max}s）",
                seg.id,
            )
        return CheckResult(
            "segment_duration", "pass",
            f"段{seg.id} 时长 {seg.duration}s 合理", seg.id,
        )

    def _check_text_length(self, seg: Segment) -> CheckResult:
        t = seg.text.strip()
        if len(t) < self.text_min_len:
            return CheckResult(
                "text_length", "warn",
                f"段{seg.id} 文案仅 {len(t)} 字（建议 {self.text_min_len}~{self.text_max_len} 字）",
                seg.id,
            )
        if len(t) > self.text_max_len:
            return CheckResult(
                "text_length", "warn",
                f"段{seg.id} 文案 {len(t)} 字偏长（建议 {self.text_min_len}~{self.text_max_len} 字）",
                seg.id,
            )
        return CheckResult(
            "text_length", "pass", f"段{seg.id} 文案 {len(t)} 字长度合适", seg.id,
        )

    def _check_keywords(self, seg: Segment) -> CheckResult:
        kw = [k for k in seg.keywords if k.strip()]
        if len(kw) < self.min_keywords:
            return CheckResult(
                "keywords", "warn",
                f"段{seg.id} 关键词 {len(kw)} 个，建议至少 {self.min_keywords} 个",
                seg.id,
            )
        return CheckResult(
            "keywords", "pass", f"段{seg.id} 关键词 {len(kw)} 个", seg.id,
        )

    def _check_emotion(self, seg: Segment) -> CheckResult:
        if seg.emotion not in _VALID_EMOTIONS:
            return CheckResult(
                "emotion", "warn",
                f"段{seg.id} 情绪 \"{seg.emotion}\" 无效（有效值: {', '.join(sorted(_VALID_EMOTIONS))}）",
                seg.id,
            )
        return CheckResult(
            "emotion", "pass", f"段{seg.id} 情绪 \"{seg.emotion}\" 有效", seg.id,
        )

    def _check_emotion_sequence(self, script: Script) -> list[CheckResult]:
        results = []
        segs = script.segments
        for i in range(1, len(segs)):
            prev_e = segs[i - 1].emotion
            curr_e = segs[i].emotion
            allowed = _EMOTION_TRANSITIONS.get(prev_e, set())
            if curr_e not in allowed:
                results.append(CheckResult(
                    "emotion_sequence", "warn",
                    f"段{segs[i-1].id}({prev_e}) → 段{segs[i].id}({curr_e}) 情绪未变化",
                    segs[i].id,
                ))
        if not results:
            results.append(CheckResult(
                "emotion_sequence", "pass", "相邻段情绪有变化",
            ))
        return results

    def _check_keyword_diversity(self, script: Script) -> list[CheckResult]:
        results = []
        segs = script.segments
        for i in range(1, len(segs)):
            prev_kw = set(k.lower() for k in segs[i - 1].keywords)
            curr_kw = set(k.lower() for k in segs[i].keywords)
            overlap = prev_kw & curr_kw
            if overlap and len(overlap) == len(curr_kw):
                results.append(CheckResult(
                    "keyword_diversity", "warn",
                    f"段{segs[i-1].id} 与 段{segs[i].id} 关键词完全相同（{', '.join(sorted(overlap))}）",
                    segs[i].id,
                ))
        if not results:
            results.append(CheckResult(
                "keyword_diversity", "pass", "相邻段关键词有差异",
            ))
        return results

    def _check_voice(self, script: Script) -> CheckResult:
        if script.voice not in _VALID_VOICES:
            return CheckResult(
                "voice", "warn",
                f"配音 \"{script.voice}\" 非标准 edge-tts 中文声音",
            )
        return CheckResult("voice", "pass", f"配音 \"{script.voice}\" 有效")

    def _check_style(self, script: Script) -> CheckResult:
        if script.style not in _VALID_STYLES:
            return CheckResult(
                "style", "warn",
                f"风格 \"{script.style}\" 非标准值（有效值: {', '.join(sorted(_VALID_STYLES))}）",
            )
        return CheckResult("style", "pass", f"风格 \"{script.style}\" 有效")

    def _check_bgm(self, script: Script) -> CheckResult:
        if not script.bgm:
            return CheckResult(
                "bgm", "warn", "未设置背景音乐推荐，建议在 AI 规划中指定 BGM",
            )
        return CheckResult("bgm", "pass", f"背景音乐 \"{script.bgm}\"")

    def _check_total_duration_match(self, script: Script) -> CheckResult:
        seg_sum = sum(s.duration for s in script.segments)
        diff = abs(script.duration - seg_sum)
        if diff > self.duration_tolerance:
            return CheckResult(
                "duration_match", "warn",
                f"脚本总时长 {script.duration}s 与各段之和 {seg_sum}s 相差 {diff}s（允许 ±{self.duration_tolerance}s）",
            )
        if script.duration > self.total_duration_max:
            return CheckResult(
                "duration_match", "warn",
                f"总时长 {script.duration}s 超过建议上限 {self.total_duration_max}s",
            )
        return CheckResult(
            "duration_match", "pass", f"总时长 {script.duration}s 与各段之和 {seg_sum}s 一致",
        )

    @staticmethod
    def summary_text(summary: QASummary) -> str:
        parts = [f"通过 {summary.passed}/{summary.total}"]
        if summary.warnings:
            parts.append(f"警告 {summary.warnings}")
        if summary.failures:
            parts.append(f"失败 {summary.failures}")
        return " · ".join(parts)
