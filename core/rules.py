from typing import Any


class Rule:
    name: str = ""
    priority: int = 0

    def apply(self, context: dict) -> dict:
        raise NotImplementedError


class RuleEngine:
    def __init__(self):
        self._rules: list[Rule] = []

    def register(self, rule: Rule):
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority)

    def register_defaults(self):
        self.register(SubtitleStyleRule())
        self.register(TransitionRule())
        self.register(CameraRule())
        self.register(DurationRule())

    def execute(self, context: dict) -> dict:
        result = {}
        for rule in self._rules:
            try:
                output = rule.apply(context)
                if output:
                    result.update(output)
            except Exception:
                continue
        return result


class SubtitleStyleRule(Rule):
    name = "subtitle_style"
    priority = 10

    EMOTION_MAP: dict[str, dict] = {
        "strong":  {"style": "big_yellow", "animation": "pulse",  "font_size": 48, "color": "#FFD700", "bold": True},
        "sad":     {"style": "soft_white", "animation": "fadein", "font_size": 36, "color": "#FFFFFF", "bold": False},
        "happy":   {"style": "bold",       "animation": "swing",  "font_size": 42, "color": "#FF6B6B", "bold": True},
        "calm":    {"style": "calm",       "animation": "scale",  "font_size": 36, "color": "#E0E0E0", "bold": False},
        "normal":  {"style": "normal",     "animation": "none",   "font_size": 36, "color": "#FFFFFF", "bold": False},
    }

    STYLE_FORCE: dict[str, str] = {
        "scifi": "scifi",
        "tech":  "tech",
    }

    def apply(self, ctx: dict) -> dict:
        emotion = ctx.get("emotion", "normal")
        result = dict(self.EMOTION_MAP.get(emotion, self.EMOTION_MAP["normal"]))

        from core.config import get_config
        sub_cfg = get_config().get("subtitle", {})
        if sub_cfg.get("font_family"):
            result["style"] = "custom"
            cfg_anim = sub_cfg.get("animation", "none")
            if cfg_anim in ("none", "pulse", "swing", "fadein", "scale", "typing"):
                result["animation"] = cfg_anim

        style = ctx.get("style")
        force = self.STYLE_FORCE.get(style) if style else None
        if force:
            result["style"] = force
            result["animation"] = "typing" if style == "scifi" else "none"

        return {"subtitle": result, "subtitle_animation": result["animation"]}


class TransitionRule(Rule):
    name = "transition"
    priority = 8

    EMOTION_TRANSITIONS: dict[tuple[str, str], str] = {
        ("normal", "normal"):     "dissolve",
        ("normal", "strong"):     "fade",
        ("normal", "calm"):       "fadeblack",
        ("strong", "strong"):     "circleopen",
        ("strong", "calm"):       "fade",
        ("calm", "normal"):       "fadewhite",
        ("calm", "calm"):         "dissolve",
        ("strong", "normal"):     "dissolve",
        ("calm", "strong"):       "fade",
    }

    def apply(self, ctx: dict) -> dict:
        duration = ctx.get("duration", 5)
        if duration <= 3:
            return {"transition": "cut"}

        prev = ctx.get("prev_emotion")
        cur = ctx.get("emotion", "normal")
        if prev and (prev, cur) in self.EMOTION_TRANSITIONS:
            trans = self.EMOTION_TRANSITIONS[(prev, cur)]
        elif prev:
            trans = "dissolve"
        else:
            trans = "fade"
        return {"transition": trans}


class CameraRule(Rule):
    name = "camera"
    priority = 6

    def apply(self, ctx: dict) -> dict:
        style = ctx.get("style", "knowledge")
        camera_map = {
            "knowledge":     "slow_zoom",
            "news":          "static",
            "entertainment": "pan",
            "commerce":      "slow_zoom",
        }
        return {"camera": camera_map.get(style, "static")}


class DurationRule(Rule):
    name = "duration_adjust"
    priority = 5

    def apply(self, ctx: dict) -> dict:
        duration = ctx.get("duration", 5)
        emotion = ctx.get("emotion", "normal")
        if emotion == "strong" and duration < 4:
            return {"adjusted_duration": 4}
        if emotion == "calm" and duration > 8:
            return {"adjusted_duration": 8}
        return {}
