from typing import Optional
from core.models import Script, Timeline, TimelineItem, Segment
from core.matcher import Matcher
from core.rules import RuleEngine


class TimelineBuilder:
    def __init__(self, matcher: Matcher, rule_engine: RuleEngine):
        self.matcher = matcher
        self.rules = rule_engine

    def build(
        self,
        script: Script,
        resolution: tuple[int, int] = (1920, 1080),
        fps: int = 30,
    ) -> Timeline:
        items: list[TimelineItem] = []
        current_time = 0.0

        for i, seg in enumerate(script.segments):
            prev_emotion = script.segments[i - 1].emotion if i > 0 else None
            item = self._build_item(seg, script, current_time, prev_emotion)
            items.append(item)
            current_time = item.end

        return Timeline(
            timeline=items,
            resolution=resolution,
            fps=fps,
        )

    def _build_item(self, seg: Segment, script: Script, start_time: float,
                    prev_emotion: str | None = None) -> TimelineItem:
        assets = self.matcher.match(
            text=seg.text,
            keywords=seg.keywords,
            top_k=1,
        )
        matched_asset = assets[0] if assets else None

        rule_ctx = {
            "emotion": seg.emotion,
            "duration": seg.duration,
            "style": script.style,
        }
        if prev_emotion is not None:
            rule_ctx["prev_emotion"] = prev_emotion
        rule_result = self.rules.execute(rule_ctx)

        duration = rule_result.get("adjusted_duration", seg.duration)
        sub_style = rule_result.get("subtitle", {})
        if isinstance(sub_style, dict):
            sub_style_name = sub_style.get("style", "normal")
        else:
            sub_style_name = str(sub_style)

        return TimelineItem(
            start=start_time,
            end=start_time + duration,
            asset=matched_asset.file if matched_asset else "",
            asset_type=matched_asset.type if matched_asset else "video",
            transition=rule_result.get("transition", "cut"),
            subtitle=seg.text,
            subtitle_style=sub_style_name,
            camera=rule_result.get("camera", "static"),
        )


class TimelineValidator:
    def validate(self, timeline: Timeline) -> list[str]:
        errors: list[str] = []

        if not timeline.timeline:
            errors.append("Timeline 为空")
            return errors

        for i, item in enumerate(timeline.timeline):
            if item.end <= item.start:
                errors.append(f"镜头 {i}: end({item.end}) <= start({item.start})")

            if i > 0:
                prev = timeline.timeline[i - 1]
                if abs(item.start - prev.end) > 0.01:
                    errors.append(f"镜头 {i}: start({item.start}) != prev end({prev.end})，存在间隙或重叠")

        if timeline.resolution:
            w, h = timeline.resolution
            if w <= 0 or h <= 0:
                errors.append(f"分辨率无效: {w}x{h}")

        total_dur = timeline.timeline[-1].end if timeline.timeline else 0
        voice_count = sum(1 for it in timeline.timeline
                          if hasattr(it, 'voice_file') and it.voice_file)
        if voice_count > 60:
            errors.append(
                f"配音段落数 {voice_count} 超过上限 60（FFmpeg amix 限制），请合并短段落"
            )
        if total_dur > 3600:
            errors.append(f"视频总时长 {total_dur:.0f}s 超过上限 3600 秒")

        return errors
