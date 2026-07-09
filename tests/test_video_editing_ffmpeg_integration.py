from __future__ import annotations

import math
import shutil
import struct
import wave
from pathlib import Path

import pytest
from PIL import Image

from app.agents.video_editing import VideoEditingAgent
from app.services.video_editing import VideoEditingRequest

pytestmark = pytest.mark.no_db


def write_tone(path: Path, *, frequency: float, duration: float) -> None:
    sample_rate = 22050
    frame_count = int(sample_rate * duration)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        for frame in range(frame_count):
            sample = int(8000 * math.sin(2 * math.pi * frequency * frame / sample_rate))
            output.writeframesraw(struct.pack("<h", sample))


@pytest.mark.asyncio
@pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="FFmpeg is not installed",
)
async def test_real_ffmpeg_render_exports_vertical_mp4(tmp_path) -> None:
    image_path = tmp_path / "scene.png"
    Image.new("RGB", (540, 960), color=(18, 92, 140)).save(image_path)
    voice_path = tmp_path / "voice.wav"
    music_path = tmp_path / "music.wav"
    write_tone(voice_path, frequency=440, duration=1.2)
    write_tone(music_path, frequency=220, duration=2)

    agent = VideoEditingAgent.from_settings()
    agent.output_dir = tmp_path / "output"
    result = await agent.render(
        VideoEditingRequest(
            visuals=[str(image_path)],
            voiceover_path=str(voice_path),
            background_music_path=str(music_path),
            script="A real subtitle is burned into this vertical test video.",
            output_prefix="integration",
            min_duration_seconds=2,
            max_duration_seconds=2,
        )
    )

    output = Path(result.video_path)
    assert output.exists()
    assert output.stat().st_size > 10_000
    assert result.width == 1080
    assert result.height == 1920
    assert 1.9 <= result.duration <= 2.1
