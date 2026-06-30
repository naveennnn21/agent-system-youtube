"""Media duration probing with ffprobe and MoviePy fallback."""

from __future__ import annotations

import json
import subprocess


class MediaProbe:
    """Probe media metadata using FFprobe, falling back to MoviePy."""

    def __init__(self, *, ffprobe_binary: str = "ffprobe") -> None:
        self.ffprobe_binary = ffprobe_binary

    def duration(self, path: str) -> float:
        ffprobe_duration = self._ffprobe_duration(path)
        if ffprobe_duration > 0:
            return ffprobe_duration
        return self._moviepy_duration(path)

    def _ffprobe_duration(self, path: str) -> float:
        command = [
            self.ffprobe_binary,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            path,
        ]
        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)
            return round(float(payload["format"]["duration"]), 3)
        except (subprocess.SubprocessError, KeyError, ValueError, json.JSONDecodeError):
            return 0.0

    def _moviepy_duration(self, path: str) -> float:
        try:
            from moviepy import AudioFileClip, VideoFileClip
        except ImportError:
            return 0.0

        for clip_cls in (AudioFileClip, VideoFileClip):
            try:
                with clip_cls(path) as clip:
                    return round(float(clip.duration or 0), 3)
            except Exception:
                continue
        return 0.0
