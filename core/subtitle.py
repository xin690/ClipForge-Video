import os
from pathlib import Path
from typing import Optional


class SubtitleGenerator:
    def __init__(self, config: dict):
        self.mode = config.get("subtitle", {}).get("engine", "text")
        self.whisper_model = config.get("subtitle", {}).get("whisper_model", "tiny")
        self.device = config.get("subtitle", {}).get("device", "cpu")
        cache_dir = config.get("paths", {}).get("cache", "./cache")
        self.cache_dir = Path(cache_dir) / "subtitle"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def generate_from_text(
        self,
        segments: list[tuple[float, float, str, Optional[str]]],
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

    def _format_ass(self, segments: list[tuple[float, float, str, Optional[str]]]) -> str:
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
            if len(seg) == 4:
                start, end, text, seg_style = seg
            else:
                start, end, text = seg
                seg_style = "Default"
            clean_text = text.strip().replace("\n", "\\N")
            events.append(
                f"Dialogue: 0,{self._time_str_ass(start)},{self._time_str_ass(end)},{seg_style},,0,0,0,,{clean_text}"
            )

        return header + "\n".join(events)

    def _get_all_ass_styles(self) -> dict[str, str]:
        return {
            "Default":     "Microsoft YaHei,36,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1",
            "normal":      "Microsoft YaHei,36,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1",
            "big_yellow":  "Microsoft YaHei,48,&H0000FFD7,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1",
            "soft_white":  "Microsoft YaHei,36,&H00E0E0E0,&H000000FF,&H00000000,&H60000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1",
            "bold":        "Microsoft YaHei,42,&H006B6BFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1",
        }

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
