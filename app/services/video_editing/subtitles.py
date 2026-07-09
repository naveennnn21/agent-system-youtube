"""Subtitle cue generation and ASS rendering."""

from __future__ import annotations

import html
import re
from pathlib import Path

from app.services.video_editing.models import SubtitleCue
from app.services.video_editing.script_text import normalize_script_text


class SubtitleGenerator:
    """Generate timed subtitle cues from script text."""

    def __init__(
        self,
        *,
        font: str = "Arial",
        font_size: int = 64,
        primary_color: str = "&H00FFFFFF",
        outline_color: str = "&H00000000",
        back_color: str = "&H80000000",
    ) -> None:
        self.font = font
        self.font_size = font_size
        self.primary_color = primary_color
        self.outline_color = outline_color
        self.back_color = back_color

    def generate_cues(
        self,
        script: str | dict[str, str],
        *,
        duration: float,
        max_words: int = 7,
    ) -> list[SubtitleCue]:
        text = normalize_script_text(script)
        words = _words(text)
        if not words or duration <= 0:
            return []

        chunks = [
            " ".join(words[index : index + max_words])
            for index in range(0, len(words), max_words)
        ]
        seconds_per_word = duration / len(words)
        cues: list[SubtitleCue] = []
        elapsed_words = 0
        for index, chunk in enumerate(chunks, start=1):
            word_count = len(_words(chunk))
            start = round(elapsed_words * seconds_per_word, 3)
            end = round(
                min(duration, (elapsed_words + word_count) * seconds_per_word), 3
            )
            if index == len(chunks):
                end = round(duration, 3)
            cues.append(
                SubtitleCue(
                    index=index, start_seconds=start, end_seconds=end, text=chunk
                )
            )
            elapsed_words += word_count
        return cues

    def write_ass(
        self,
        cues: list[SubtitleCue],
        *,
        path: str | Path,
        width: int,
        height: int,
    ) -> str:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {width}",
            f"PlayResY: {height}",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            (
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
                "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                "Alignment, MarginL, MarginR, MarginV, Encoding"
            ),
            (
                f"Style: Default,{self.font},{self.font_size},{self.primary_color},"
                f"&H000000FF,{self.outline_color},{self.back_color},-1,0,0,0,"
                "100,100,0,0,1,4,1,2,80,80,180,1"
            ),
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]
        for cue in cues:
            text = _ass_escape(cue.text)
            lines.append(
                "Dialogue: 0,"
                f"{_ass_time(cue.start_seconds)},"
                f"{_ass_time(cue.end_seconds)},"
                f"Default,,0,0,0,,{text}"
            )

        output.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return str(output)


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", text)


def _ass_escape(text: str) -> str:
    escaped = html.escape(text, quote=False)
    return escaped.replace("{", "").replace("}", "").replace("\n", r"\N")


def _ass_time(seconds: float) -> str:
    total = max(0, int(seconds * 100))
    centiseconds = total % 100
    total_seconds = total // 100
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"
