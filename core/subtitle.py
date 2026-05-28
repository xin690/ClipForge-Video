import os
from pathlib import Path
from typing import Optional


ANIMATION_TAGS: dict[str, str] = {
    "pulse":    "{\\t(0,300,\\fs44\\fs52)}",
    "swing":    "{\\t(0,400,\\frz-5\\frz5)}",
    "fadein":   "{\\t(0,500,\\alpha&HFF&\\alpha&H00&)}",
    "scale":    "{\\t(0,600,\\fscx105\\fscy105)}",
    "typing":   "{\\t(0,800,\\fscx0\\fscx100)}",
    "slide_up": "{\\t(0,400,\\pos($x,$y)\\pos($x,$y-40))}",
    "typewriter": "{\\t(0,1000,\\clip(0,0,0,1080)\\clip(0,0,1920,1080))}",
    "bounce":   "{\\t(0,300,\\fs36\\fs44)\\t(300,600,\\fs44\\fs36)\\t(600,800,\\fs36\\fs42)\\t(800,1000,\\fs42\\fs36)}",
    "glow":     "{\\t(0,500,\\bord2\\bord6\\bord2)}",
}

POSITION_ALIGN: dict[str, int] = {
    "bottom": 2,
    "top": 8,
    "center": 5,
    "bottom_left": 1,
    "bottom_right": 3,
    "top_left": 7,
    "top_right": 9,
    "middle_left": 4,
    "middle_right": 6,
}


def _html_color_to_ass(html: str) -> str:
    """Convert #RRGGBB to &H00BBGGRR (ASS color format)."""
    h = html.lstrip("#")
    if len(h) != 6:
        return "&H00FFFFFF"
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}"


def _build_style_string(font: str, size: int, color: str, bold: bool = False,
                        outline: int = 2, shadow: int = 1,
                        position: str = "bottom", margin_v: int = 10) -> str:
    primary = _html_color_to_ass(color)
    align = POSITION_ALIGN.get(position, 2)
    b = "-1" if bold else "0"
    return (f"{font},{size},{primary},&H000000FF,&H00000000,"
            f"&H80000000,{b},0,0,0,100,100,0,0,1,{outline},{shadow},"
            f"{align},10,{margin_v},10,1")


class SubtitleGenerator:
    def __init__(self, config: dict):
        self._config = config
        self.mode = config.get("subtitle", {}).get("engine", "text")
        self.whisper_model = config.get("subtitle", {}).get("whisper_model", "tiny")
        self.device = config.get("subtitle", {}).get("device", "cpu")
        cache_dir = config.get("paths", {}).get("cache", "./cache")
        self.cache_dir = Path(cache_dir) / "subtitle"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def generate_from_text(
        self,
        segments: list,
        output_path: str,
        style: str = "normal",
    ) -> str:
        ext = Path(output_path).suffix.lower()
        if ext == ".ass":
            content = self._format_ass(segments)
        else:
            content = self._format_srt(segments)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return output_path

    def generate_from_audio(
        self,
        audio_path: str,
        script_segments: list[tuple[int, str]],
        output_path: str,
        style: str = "normal",
    ) -> str:
        text_segments: list[tuple[float, float, str, str]] = []

        if not os.path.exists(audio_path):
            for i, (_, text) in enumerate(script_segments):
                text_segments.append((i * 5.0, (i + 1) * 5.0, text, style))
            return self.generate_from_text(text_segments, output_path)

        try:
            from faster_whisper import WhisperModel

            model = WhisperModel(self.whisper_model, device=self.device, compute_type="int8")
            segments_gen, info = model.transcribe(audio_path, language="zh")

            for seg in segments_gen:
                text_segments.append((seg.start, seg.end, seg.text, style))

            return self.generate_from_text(text_segments, output_path)
        except Exception:
            text_segments = []
            for i, (_, text) in enumerate(script_segments):
                text_segments.append((i * 5.0, (i + 1) * 5.0, text, style))
            return self.generate_from_text(text_segments, output_path)

    def _format_srt(self, segments: list[tuple[float, float, str]]) -> str:
        lines = []
        for i, seg in enumerate(segments, 1):
            start, end, text = seg[:3]
            lines.append(str(i))
            lines.append(f"{self._time_str_srt(start)} --> {self._time_str_srt(end)}")
            lines.append(text.strip())
            lines.append("")
        return "\n".join(lines)

    def _format_ass(self, segments: list) -> str:
        style_lines = "\n".join(
            f"Style: {name},{defn}"
            for name, defn in self._get_all_ass_styles().items()
        )

        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginV, MarginR, Encoding
{style_lines}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []
        for seg in segments:
            start, end, text, seg_style, animation = (None, None, "", "Default", "none")
            position = None
            margin_v = 0
            if len(seg) >= 7:
                start, end, text, seg_style, animation, position, margin_v = seg[:7]
            elif len(seg) >= 6:
                start, end, text, seg_style, animation, position = seg[:6]
            elif len(seg) == 5:
                start, end, text, seg_style, animation = seg[:5]
            elif len(seg) == 4:
                start, end, text, seg_style = seg[:4]
            elif len(seg) == 3:
                start, end, text = seg[:3]
            else:
                continue
            clean_text = text.strip().replace("\n", "\\N")
            anim_tag = ANIMATION_TAGS.get(animation, "")
            if anim_tag:
                clean_text = anim_tag + clean_text
            if position and position in POSITION_ALIGN:
                style_align = self._get_style_alignment(seg_style)
                target_align = POSITION_ALIGN[position]
                if target_align != style_align:
                    clean_text = f"{{\\an{target_align}}}{clean_text}"
            events.append(
                f"Dialogue: 0,{self._time_str_ass(start)},{self._time_str_ass(end)},{seg_style},,0,0,{margin_v},,{clean_text}"
            )

        return header + "\n".join(events)

    def _get_style_alignment(self, style_name: str) -> int:
        style_str = self._get_all_ass_styles().get(style_name, "")
        if not style_str:
            return 2
        parts = style_str.split(",")
        if len(parts) >= 18:
            try:
                return int(parts[17])
            except ValueError:
                pass
        return 2

    ALL_ASS_STYLES: dict[str, str] = {
    "Default":       "Microsoft YaHei,36,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1",
    "normal":        "Microsoft YaHei,36,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1",
    "big_yellow":    "Microsoft YaHei,48,&H0000FFD7,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1",
    "soft_white":    "Microsoft YaHei,36,&H00E0E0E0,&H000000FF,&H00000000,&H60000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1",
    "bold":          "Microsoft YaHei,42,&H006B6BFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1",
    "strong":        "Microsoft YaHei,48,&H0000FFD7,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1",
    "happy":         "Microsoft YaHei,42,&H006B6BFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1",
    "sad":           "Microsoft YaHei,36,&H00E0E0E0,&H000000FF,&H00000000,&H60000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1",
    "calm":          "Noto Sans SC,36,&H00C0C0C0,&H000000FF,&H00000000,&H40000000,0,0,0,0,100,100,0,0,1,1,1,2,10,10,10,1",
    "knowledge":     "Microsoft YaHei,38,&H00FFFFFF,&H000000FF,&H004466AA,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,10,30,10,1",
    "news":          "Microsoft YaHei,42,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,2,2,20,20,20,1",
    "entertainment": "Noto Sans SC,46,&H0000FFD7,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,2,1,8,10,10,10,1",
    "commerce":      "Microsoft YaHei,44,&H0000FFD7,&H000000FF,&H00222222,&H80000000,-1,0,0,0,100,100,0,0,1,2,3,2,10,10,10,1",
    "scifi":         "Consolas,40,&H00CCFF00,&H000000FF,&H00448800,&H80000000,-1,0,0,0,100,100,3,0,1,2,1,2,10,10,10,1",
    "tech":          "Consolas,38,&H00FFFFFF,&H000000FF,&H0033AA33,&HAA000000,0,0,0,0,100,100,0,0,3,0,0,2,10,10,10,1",
    "keyword":       "Microsoft YaHei,28,&H00888888,&H000000FF,&H00000000,&H60000000,0,0,0,0,100,100,0,0,1,1,0,8,10,10,10,1",
}

    def _get_all_ass_styles(self) -> dict[str, str]:
        styles = dict(self.ALL_ASS_STYLES)
        sub_cfg = getattr(self, '_config', {}).get("subtitle", {})
        margin_v = sub_cfg.get("margin_v", 10)
        for name in list(styles.keys()):
            parts = styles[name].split(",")
            if len(parts) > 20:
                parts[19] = str(margin_v)
                styles[name] = ",".join(parts)
        if sub_cfg.get("font_family"):
            styles["custom"] = _build_style_string(
                font=sub_cfg.get("font_family", "Microsoft YaHei"),
                size=sub_cfg.get("font_size", 36),
                color=sub_cfg.get("font_color", "#FFFFFF"),
                bold=sub_cfg.get("bold", False),
                outline=sub_cfg.get("outline", 2),
                shadow=sub_cfg.get("shadow", 1),
                position=sub_cfg.get("position", "bottom"),
                margin_v=margin_v,
            )
        return styles

    def _get_ass_style(self, style: str) -> str:
        styles = {
            "normal":      "Microsoft YaHei,36,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1",
            "big_yellow":  "Microsoft YaHei,48,&H0000FFD7,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1",
            "soft_white":  "Microsoft YaHei,36,&H00E0E0E0,&H000000FF,&H00000000,&H60000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1",
            "bold":        "Microsoft YaHei,42,&H006B6BFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1",
        }
        return styles.get(style, styles["normal"])

    def _time_str_srt(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

    def _time_str_ass(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        sec = int(seconds % 60)
        centi = int((seconds - int(seconds)) * 100)
        return f"{h:01d}:{m:02d}:{sec:02d}.{centi:02d}"
