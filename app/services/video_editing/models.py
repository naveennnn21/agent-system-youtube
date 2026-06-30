"""Data models for video editing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class VisualClip:
    """Visual input for one segment of the Short."""

    asset_path: str
    duration: float | None = None
    scene_index: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VideoEditingRequest:
    """Input for rendering a 1080x1920 Short."""

    visuals: list[VisualClip | str | dict[str, Any]]
    voiceover_path: str
    script: str | dict[str, str]
    output_prefix: str = "short"
    background_music_path: str | None = None
    background_music_volume: float = 0.18
    voiceover_volume: float = 1.0
    auto_subtitles: bool = True
    subtitle_max_words: int = 7
    target_width: int = 1080
    target_height: int = 1920
    fps: int = 30
    max_duration_seconds: float = 60.0
    min_duration_seconds: float = 30.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.target_width <= 0 or self.target_height <= 0:
            raise ValueError("Video dimensions must be positive.")
        if self.fps <= 0:
            raise ValueError("Video FPS must be positive.")
        if self.min_duration_seconds <= 0:
            raise ValueError("Minimum duration must be positive.")
        if self.max_duration_seconds < self.min_duration_seconds:
            raise ValueError("Maximum duration must be at least the minimum duration.")
        if not 0 <= self.background_music_volume <= 2:
            raise ValueError("Background music volume must be between 0 and 2.")
        if not 0 <= self.voiceover_volume <= 2:
            raise ValueError("Voiceover volume must be between 0 and 2.")
        if self.subtitle_max_words <= 0:
            raise ValueError("Subtitle word count must be positive.")


@dataclass(slots=True)
class SubtitleCue:
    """Timed subtitle cue."""

    index: int
    start_seconds: float
    end_seconds: float
    text: str


@dataclass(slots=True)
class VideoAsset:
    """Stored video metadata."""

    video_path: str
    width: int
    height: int
    duration: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VideoEditingResult:
    """Public video editing output."""

    video_path: str
    width: int
    height: int
    duration: float

    def to_dict(self) -> dict[str, str | int | float]:
        return {
            "video_path": self.video_path,
            "width": self.width,
            "height": self.height,
            "duration": self.duration,
        }
