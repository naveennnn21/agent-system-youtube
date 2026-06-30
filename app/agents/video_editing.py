"""Video Editing Agent using FFmpeg and MoviePy-enabled probing."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from app.core.config import Settings, get_settings
from app.services.video_editing import (
    FFmpegCommandBuilder,
    FFmpegRunner,
    MediaProbe,
    SubtitleGenerator,
    VideoEditingRequest,
    VideoEditingResult,
    VisualClip,
)
from app.services.video_editing.ffmpeg import ensure_parent


class VideoEditingError(RuntimeError):
    """Raised when a Short cannot be rendered."""


class VideoEditingAgent:
    """Combine visuals, voiceover, subtitles, and music into a vertical MP4."""

    def __init__(
        self,
        *,
        output_dir: str,
        probe: MediaProbe,
        subtitle_generator: SubtitleGenerator,
        command_builder: FFmpegCommandBuilder,
        runner: FFmpegRunner,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        min_duration_seconds: float = 30.0,
        max_duration_seconds: float = 60.0,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.probe = probe
        self.subtitle_generator = subtitle_generator
        self.command_builder = command_builder
        self.runner = runner
        self.width = width
        self.height = height
        self.fps = fps
        self.min_duration_seconds = min_duration_seconds
        self.max_duration_seconds = max_duration_seconds

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "VideoEditingAgent":
        settings = settings or get_settings()
        return cls(
            output_dir=settings.VIDEO_STORAGE_PATH,
            probe=MediaProbe(ffprobe_binary=settings.FFPROBE_BINARY),
            subtitle_generator=SubtitleGenerator(
                font=settings.VIDEO_SUBTITLE_FONT,
                font_size=settings.VIDEO_SUBTITLE_FONT_SIZE,
                primary_color=settings.VIDEO_SUBTITLE_PRIMARY_COLOR,
                outline_color=settings.VIDEO_SUBTITLE_OUTLINE_COLOR,
                back_color=settings.VIDEO_SUBTITLE_BACK_COLOR,
            ),
            command_builder=FFmpegCommandBuilder(
                ffmpeg_binary=settings.FFMPEG_BINARY,
                preset=settings.VIDEO_PRESET,
                crf=settings.VIDEO_CRF,
                audio_bitrate=settings.VIDEO_AUDIO_BITRATE,
            ),
            runner=FFmpegRunner(),
            width=settings.VIDEO_WIDTH,
            height=settings.VIDEO_HEIGHT,
            fps=settings.VIDEO_FPS,
            min_duration_seconds=settings.VIDEO_MIN_DURATION_SECONDS,
            max_duration_seconds=settings.VIDEO_MAX_DURATION_SECONDS,
        )

    async def edit_video(
        self,
        request: VideoEditingRequest,
    ) -> dict[str, str | int | float]:
        """Render a Short and return the public output contract."""
        result = await self.render(request)
        return result.to_dict()

    async def render(self, request: VideoEditingRequest) -> VideoEditingResult:
        clips = _normalize_visuals(request.visuals)
        if not clips:
            raise VideoEditingError("At least one visual asset is required.")
        if not request.voiceover_path:
            raise VideoEditingError("A voiceover path is required.")
        _validate_inputs(
            clips,
            voiceover_path=request.voiceover_path,
            background_music_path=request.background_music_path,
        )

        voice_duration = await asyncio.to_thread(
            self.probe.duration,
            request.voiceover_path,
        )
        if voice_duration <= 0:
            voice_duration = request.min_duration_seconds
        duration = min(
            request.max_duration_seconds or self.max_duration_seconds,
            max(request.min_duration_seconds or self.min_duration_seconds, voice_duration),
        )

        clips = _assign_clip_durations(clips, duration)
        output_path = self._output_path(request.output_prefix)
        ensure_parent(output_path)

        subtitle_path: str | None = None
        if request.auto_subtitles:
            cues = self.subtitle_generator.generate_cues(
                request.script,
                duration=duration,
                max_words=request.subtitle_max_words,
            )
            if cues:
                subtitle_path = str(Path(output_path).with_suffix(".ass"))
                self.subtitle_generator.write_ass(
                    cues,
                    path=subtitle_path,
                    width=request.target_width or self.width,
                    height=request.target_height or self.height,
                )

        command = self.command_builder.build(
            clips=clips,
            voiceover_path=request.voiceover_path,
            output_path=output_path,
            width=request.target_width or self.width,
            height=request.target_height or self.height,
            fps=request.fps or self.fps,
            duration=duration,
            subtitle_path=subtitle_path,
            background_music_path=request.background_music_path,
            background_music_volume=request.background_music_volume,
            voiceover_volume=request.voiceover_volume,
        )
        await asyncio.to_thread(self.runner.run, command)

        rendered_duration = (
            await asyncio.to_thread(self.probe.duration, output_path)
        ) or duration
        return VideoEditingResult(
            video_path=output_path,
            width=request.target_width or self.width,
            height=request.target_height or self.height,
            duration=round(rendered_duration, 3),
        )

    def _output_path(self, prefix: str) -> str:
        safe_prefix = "".join(char if char.isalnum() or char in "-_" else "-" for char in prefix)
        filename = f"{safe_prefix.strip('-') or 'short'}-{uuid.uuid4().hex}.mp4"
        return str(self.output_dir / filename)


def _normalize_visuals(visuals: list[VisualClip | str | dict]) -> list[VisualClip]:
    clips: list[VisualClip] = []
    for item in visuals:
        if isinstance(item, VisualClip):
            clips.append(item)
        elif isinstance(item, str):
            clips.append(VisualClip(asset_path=item))
        elif isinstance(item, dict):
            path = item.get("asset_path") or item.get("path") or item.get("visual_path")
            if path:
                clips.append(
                    VisualClip(
                        asset_path=str(path),
                        duration=item.get("duration"),
                        scene_index=item.get("scene_index"),
                        metadata=item.get("metadata", {}),
                    )
                )
    return clips


def _assign_clip_durations(clips: list[VisualClip], total_duration: float) -> list[VisualClip]:
    explicit = sum(clip.duration or 0 for clip in clips)
    missing = [clip for clip in clips if not clip.duration]
    remaining = max(0.1, total_duration - explicit)
    default_duration = remaining / len(missing) if missing else 0

    normalized: list[VisualClip] = []
    for clip in clips:
        normalized.append(
            VisualClip(
                asset_path=clip.asset_path,
                duration=round(clip.duration or default_duration, 3),
                scene_index=clip.scene_index,
                metadata=clip.metadata,
            )
        )
    return normalized


def _validate_inputs(
    clips: list[VisualClip],
    *,
    voiceover_path: str,
    background_music_path: str | None,
) -> None:
    paths = [clip.asset_path for clip in clips]
    paths.append(voiceover_path)
    if background_music_path:
        paths.append(background_music_path)

    missing = [path for path in paths if not Path(path).is_file()]
    if missing:
        raise VideoEditingError(
            "Media input does not exist: " + ", ".join(sorted(set(missing)))
        )
