from __future__ import annotations

from pathlib import Path

import pytest

from app.agents.video_editing import VideoEditingAgent, VideoEditingError
from app.services.video_editing import (
    FFmpegCommandBuilder,
    SubtitleGenerator,
    VideoEditingRequest,
    VisualClip,
)

pytestmark = pytest.mark.no_db


class FakeProbe:
    def __init__(self, duration: float = 42.0) -> None:
        self.duration_seconds = duration
        self.paths: list[str] = []

    def duration(self, path: str) -> float:
        self.paths.append(path)
        return self.duration_seconds


class FakeRunner:
    def __init__(self) -> None:
        self.command: list[str] | None = None

    def run(self, command: list[str]) -> None:
        self.command = command
        Path(command[-1]).write_bytes(b"fake-mp4")


def touch(path: Path) -> str:
    path.write_bytes(b"media")
    return str(path)


def test_subtitle_generator_writes_timed_ass_file(tmp_path) -> None:
    generator = SubtitleGenerator(font="Arial", font_size=60)
    cues = generator.generate_cues(
        {
            "hook": "Stop scrolling.",
            "script": "This editing trick keeps every scene moving.",
            "cta": "Save it.",
        },
        duration=12,
        max_words=3,
    )

    output = generator.write_ass(
        cues,
        path=tmp_path / "captions.ass",
        width=1080,
        height=1920,
    )
    content = Path(output).read_text(encoding="utf-8")

    assert cues[0].start_seconds == 0
    assert cues[-1].end_seconds == 12
    assert "PlayResX: 1080" in content
    assert "PlayResY: 1920" in content
    assert "Dialogue: 0," in content


def test_ffmpeg_builder_combines_images_video_audio_music_and_subtitles() -> None:
    builder = FFmpegCommandBuilder()
    command = builder.build(
        clips=[
            VisualClip(asset_path="scene-1.png", duration=10),
            VisualClip(asset_path="scene-2.mp4", duration=20),
        ],
        voiceover_path="voice.mp3",
        background_music_path="music.mp3",
        subtitle_path="captions.ass",
        output_path="short.mp4",
        width=1080,
        height=1920,
        fps=30,
        duration=30,
    )
    joined = " ".join(command)

    assert "-loop 1 -t 10.000 -i scene-1.png" in joined
    assert "-stream_loop -1 -t 20.000 -i scene-2.mp4" in joined
    assert "scale=1080:1920" in joined
    assert "crop=1080:1920" in joined
    assert "concat=n=2:v=1:a=0" in joined
    assert "subtitles='captions.ass'" in joined
    assert "apad=pad_dur=30.000" in joined
    assert "amix=inputs=2:duration=first" in joined
    assert "-c:v libx264" in joined
    assert "-c:a aac" in joined
    assert "-pix_fmt yuv420p" in joined
    assert command[-1] == "short.mp4"


@pytest.mark.asyncio
async def test_video_agent_renders_vertical_short_with_subtitles(tmp_path) -> None:
    image = touch(tmp_path / "scene.png")
    video = touch(tmp_path / "scene.mp4")
    voice = touch(tmp_path / "voice.mp3")
    music = touch(tmp_path / "music.mp3")
    runner = FakeRunner()
    probe = FakeProbe(duration=42)
    agent = VideoEditingAgent(
        output_dir=str(tmp_path / "output"),
        probe=probe,
        subtitle_generator=SubtitleGenerator(),
        command_builder=FFmpegCommandBuilder(),
        runner=runner,
    )

    result = await agent.render(
        VideoEditingRequest(
            visuals=[
                image,
                {"asset_path": video, "scene_index": 2},
            ],
            voiceover_path=voice,
            background_music_path=music,
            script={
                "hook": "This changes everything.",
                "script": "Use motion and captions to hold attention.",
                "cta": "Try it today.",
            },
            output_prefix="editing test",
        )
    )

    assert result.width == 1080
    assert result.height == 1920
    assert result.duration == 42
    assert Path(result.video_path).exists()
    assert Path(result.video_path).with_suffix(".ass").exists()
    assert runner.command is not None
    assert "-filter_complex" in runner.command
    assert "42.000" in " ".join(runner.command)


@pytest.mark.asyncio
async def test_video_agent_rejects_missing_media(tmp_path) -> None:
    agent = VideoEditingAgent(
        output_dir=str(tmp_path / "output"),
        probe=FakeProbe(),
        subtitle_generator=SubtitleGenerator(),
        command_builder=FFmpegCommandBuilder(),
        runner=FakeRunner(),
    )

    with pytest.raises(VideoEditingError, match="Media input does not exist"):
        await agent.render(
            VideoEditingRequest(
                visuals=[str(tmp_path / "missing.png")],
                voiceover_path=str(tmp_path / "missing.mp3"),
                script="A complete short script.",
            )
        )


def test_video_request_validates_duration_range() -> None:
    with pytest.raises(ValueError, match="Maximum duration"):
        VideoEditingRequest(
            visuals=["scene.png"],
            voiceover_path="voice.mp3",
            script="Script",
            min_duration_seconds=60,
            max_duration_seconds=30,
        )
