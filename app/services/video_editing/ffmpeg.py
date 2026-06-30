"""FFmpeg command building and execution."""

from __future__ import annotations

import subprocess
from pathlib import Path

from app.services.video_editing.models import VisualClip


class FFmpegRenderError(RuntimeError):
    """Raised when FFmpeg fails."""


class FFmpegCommandBuilder:
    """Build production FFmpeg commands for 1080x1920 Shorts exports."""

    def __init__(
        self,
        *,
        ffmpeg_binary: str = "ffmpeg",
        video_codec: str = "libx264",
        audio_codec: str = "aac",
        preset: str = "veryfast",
        crf: int = 18,
        audio_bitrate: str = "192k",
    ) -> None:
        self.ffmpeg_binary = ffmpeg_binary
        self.video_codec = video_codec
        self.audio_codec = audio_codec
        self.preset = preset
        self.crf = crf
        self.audio_bitrate = audio_bitrate

    def build(
        self,
        *,
        clips: list[VisualClip],
        voiceover_path: str,
        output_path: str,
        width: int,
        height: int,
        fps: int,
        duration: float,
        subtitle_path: str | None = None,
        background_music_path: str | None = None,
        background_music_volume: float = 0.18,
        voiceover_volume: float = 1.0,
    ) -> list[str]:
        if not clips:
            raise ValueError("At least one visual clip is required.")

        command = [self.ffmpeg_binary, "-y", "-hide_banner"]
        for clip in clips:
            if _is_still_image(clip.asset_path):
                command.extend(["-loop", "1"])
            else:
                command.extend(["-stream_loop", "-1"])
            command.extend(
                [
                    "-t",
                    _seconds(clip.duration or duration / len(clips)),
                    "-i",
                    clip.asset_path,
                ]
            )

        voice_index = len(clips)
        command.extend(["-i", voiceover_path])
        music_index: int | None = None
        if background_music_path:
            music_index = len(clips) + 1
            command.extend(["-stream_loop", "-1", "-i", background_music_path])

        filter_complex = self._filter_complex(
            clips=clips,
            width=width,
            height=height,
            fps=fps,
            subtitle_path=subtitle_path,
            voice_index=voice_index,
            music_index=music_index,
            background_music_volume=background_music_volume,
            voiceover_volume=voiceover_volume,
            duration=duration,
        )
        command.extend(
            [
                "-filter_complex",
                filter_complex,
                "-map",
                "[vout]",
                "-map",
                "[aout]",
                "-c:v",
                self.video_codec,
                "-preset",
                self.preset,
                "-crf",
                str(self.crf),
                "-pix_fmt",
                "yuv420p",
                "-r",
                str(fps),
                "-c:a",
                self.audio_codec,
                "-b:a",
                self.audio_bitrate,
                "-movflags",
                "+faststart",
                "-t",
                _seconds(duration),
                "-shortest",
                output_path,
            ]
        )
        return command

    def _filter_complex(
        self,
        *,
        clips: list[VisualClip],
        width: int,
        height: int,
        fps: int,
        subtitle_path: str | None,
        voice_index: int,
        music_index: int | None,
        background_music_volume: float,
        voiceover_volume: float,
        duration: float,
    ) -> str:
        chains: list[str] = []
        concat_inputs = ""
        for index, _clip in enumerate(clips):
            label = f"v{index}"
            chains.append(
                f"[{index}:v]"
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},setsar=1,fps={fps},format=yuv420p"
                f"[{label}]"
            )
            concat_inputs += f"[{label}]"

        video_chain = f"{concat_inputs}concat=n={len(clips)}:v=1:a=0[vbase]"
        if subtitle_path:
            video_chain += (
                f";[vbase]subtitles='{_escape_filter_path(subtitle_path)}'[vout]"
            )
        else:
            video_chain += ";[vbase]null[vout]"
        chains.append(video_chain)

        if music_index is None:
            chains.append(
                f"[{voice_index}:a]volume={voiceover_volume},"
                f"apad=pad_dur={_seconds(duration)}[aout]"
            )
        else:
            chains.append(
                f"[{voice_index}:a]volume={voiceover_volume},"
                f"apad=pad_dur={_seconds(duration)}[voice];"
                f"[{music_index}:a]volume={background_music_volume}[music];"
                "[voice][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            )

        return ";".join(chains)


class FFmpegRunner:
    """Run FFmpeg commands."""

    def run(self, command: list[str]) -> None:
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            message = exc.stderr or exc.stdout or str(exc)
            raise FFmpegRenderError(message) from exc


def ensure_parent(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _seconds(value: float) -> str:
    return f"{max(0.001, value):.3f}"


def _escape_filter_path(path: str) -> str:
    value = Path(path).as_posix()
    return value.replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def _is_still_image(path: str) -> bool:
    return Path(path).suffix.lower() in {
        ".bmp",
        ".jpeg",
        ".jpg",
        ".png",
        ".tif",
        ".tiff",
        ".webp",
    }
