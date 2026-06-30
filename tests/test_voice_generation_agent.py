from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from app.agents.voice_generation import VoiceGenerationAgent, VoiceGenerationError
from app.services.voice_generation import (
    ElevenLabsTTSClient,
    FileAudioStorage,
    OpenAITTSClient,
    RetryPolicy,
    VoiceGenerationRequest,
    VoiceProviderError,
    VoiceProfile,
    VoiceRegistry,
    estimate_mp3_duration,
)
from app.services.voice_generation.models import AudioAsset

pytestmark = pytest.mark.no_db


class FakeProvider:
    def __init__(
        self,
        *,
        provider: str,
        content: bytes,
        configured: bool = True,
        failures: int = 0,
        retryable: bool = True,
    ) -> None:
        self.provider = provider
        self.content = content
        self._configured = configured
        self.failures = failures
        self.retryable = retryable
        self.calls = 0

    @property
    def is_configured(self) -> bool:
        return self._configured

    async def synthesize(self, *, text: str, voice: VoiceProfile) -> AudioAsset:
        self.calls += 1
        if self.failures > 0:
            self.failures -= 1
            raise VoiceProviderError("temporary outage", retryable=self.retryable)
        return AudioAsset(
            content=self.content,
            provider=self.provider,
            voice=voice.name,
        )


def make_mp3(frames: int = 8) -> bytes:
    header = b"\xff\xfb\x90\x64"
    frame_length = 417
    frame = header + (b"\x00" * (frame_length - len(header)))
    return frame * frames


def test_estimate_mp3_duration_from_frames() -> None:
    content = make_mp3(frames=10)

    duration = estimate_mp3_duration(content)

    assert 0.25 <= duration <= 0.27


@pytest.mark.asyncio
async def test_elevenlabs_client_posts_text_to_speech_payload() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = request.headers["xi-api-key"]
        captured["accept"] = request.headers["accept"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, content=make_mp3())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = ElevenLabsTTSClient(
            api_key="eleven-key",
            client=client,
            stability=0.3,
            similarity_boost=0.7,
        )
        asset = await provider.synthesize(
            text="Hello world",
            voice=VoiceProfile(name="narrator", elevenlabs_voice_id="voice-123"),
        )

    payload = captured["payload"]
    assert captured["url"].startswith(
        "https://api.elevenlabs.io/v1/text-to-speech/voice-123"
    )
    assert "output_format=mp3_44100_128" in captured["url"]
    assert captured["api_key"] == "eleven-key"
    assert captured["accept"] == "audio/mpeg"
    assert payload["text"] == "Hello world"
    assert payload["model_id"] == "eleven_multilingual_v2"
    assert payload["voice_settings"]["stability"] == 0.3
    assert asset.provider == "elevenlabs"
    assert asset.content.startswith(b"\xff\xfb")


@pytest.mark.asyncio
async def test_openai_client_posts_audio_speech_payload() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, content=make_mp3())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAITTSClient(
            api_key="openai-key",
            model="gpt-4o-mini-tts",
            instructions="Sound excited but clear.",
            client=client,
        )
        asset = await provider.synthesize(
            text="Hello fallback",
            voice=VoiceProfile(name="warm", openai_voice="nova"),
        )

    payload = captured["payload"]
    assert captured["url"] == "https://api.openai.com/v1/audio/speech"
    assert captured["authorization"] == "Bearer openai-key"
    assert payload["model"] == "gpt-4o-mini-tts"
    assert payload["voice"] == "nova"
    assert payload["input"] == "Hello fallback"
    assert payload["response_format"] == "mp3"
    assert payload["instructions"] == "Sound excited but clear."
    assert asset.provider == "openai"


@pytest.mark.asyncio
async def test_voice_agent_retries_primary_and_stores_mp3(tmp_path) -> None:
    content = make_mp3(frames=12)
    provider = FakeProvider(
        provider="elevenlabs",
        content=content,
        failures=1,
        retryable=True,
    )
    agent = VoiceGenerationAgent(
        providers=[provider],
        storage=FileAudioStorage(tmp_path),
        retry_policy=RetryPolicy(max_attempts=2, base_delay_seconds=0),
    )

    result = await agent.generate(
        VoiceGenerationRequest(
            text="This is a generated voiceover for a short video.",
            filename_prefix="test voice",
        )
    )

    assert provider.calls == 2
    assert result.audio_path.endswith(".mp3")
    assert result.duration > 0
    assert Path(result.audio_path).exists()


@pytest.mark.asyncio
async def test_voice_agent_falls_back_to_openai(tmp_path) -> None:
    primary = FakeProvider(
        provider="elevenlabs",
        content=b"",
        failures=1,
        retryable=False,
    )
    fallback = FakeProvider(provider="openai", content=make_mp3(frames=5))
    agent = VoiceGenerationAgent(
        providers=[primary, fallback],
        storage=FileAudioStorage(tmp_path),
        retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=0),
    )

    result = await agent.generate(
        VoiceGenerationRequest(
            text="Fallback voiceover should still be generated.",
            provider_order=["elevenlabs", "openai"],
        )
    )

    assert primary.calls == 1
    assert fallback.calls == 1
    assert result.audio_path.endswith(".mp3")
    assert result.duration > 0


@pytest.mark.asyncio
async def test_voice_agent_reports_all_provider_failures(tmp_path) -> None:
    agent = VoiceGenerationAgent(
        providers=[
            FakeProvider(provider="elevenlabs", content=b"", configured=False),
            FakeProvider(provider="openai", content=b"", configured=False),
        ],
        storage=FileAudioStorage(tmp_path),
        retry_policy=RetryPolicy(max_attempts=1, base_delay_seconds=0),
    )

    with pytest.raises(VoiceGenerationError, match="All voice providers failed"):
        await agent.generate(VoiceGenerationRequest(text="Hello"))


def test_voice_registry_accepts_json_overrides() -> None:
    registry = VoiceRegistry.from_json(
        json.dumps(
            {
                "documentary": {
                    "elevenlabs_voice_id": "eleven-doc",
                    "openai_voice": "onyx",
                    "description": "Documentary narration",
                }
            }
        )
    )

    profile = registry.resolve("documentary")

    assert profile.elevenlabs_voice_id == "eleven-doc"
    assert profile.openai_voice == "onyx"
