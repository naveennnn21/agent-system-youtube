"""Voice Generation Agent with ElevenLabs primary and OpenAI fallback."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Protocol

from app.core.config import Settings, get_settings
from app.services.voice_generation import (
    AudioAsset,
    ElevenLabsTTSClient,
    FileAudioStorage,
    OpenAITTSClient,
    RetryPolicy,
    VoiceGenerationRequest,
    VoiceGenerationResult,
    VoiceProfile,
    VoiceProviderError,
    VoiceRegistry,
    estimate_mp3_duration,
)
from app.services.voice_generation.duration import estimate_spoken_duration
from app.services.voice_generation.models import VoiceProviderName

logger = logging.getLogger(__name__)


class VoiceGenerationError(RuntimeError):
    """Raised when all TTS providers fail."""


class VoiceProvider(Protocol):
    provider: VoiceProviderName

    @property
    def is_configured(self) -> bool:
        """Return whether this provider can be used."""

    async def synthesize(self, *, text: str, voice: VoiceProfile) -> AudioAsset:
        """Generate audio for a voice profile."""


class VoiceGenerationAgent:
    """Generate MP3 voiceover audio for scripts."""

    def __init__(
        self,
        *,
        providers: Iterable[VoiceProvider],
        storage: FileAudioStorage,
        voice_registry: VoiceRegistry | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.providers = {provider.provider: provider for provider in providers}
        self.storage = storage
        self.voice_registry = voice_registry or VoiceRegistry()
        self.retry_policy = retry_policy or RetryPolicy()

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "VoiceGenerationAgent":
        """Create the production voice agent from application settings."""
        settings = settings or get_settings()
        return cls(
            providers=[
                ElevenLabsTTSClient(
                    api_key=settings.ELEVENLABS_API_KEY,
                    base_url=settings.ELEVENLABS_BASE_URL,
                    model_id=settings.ELEVENLABS_MODEL_ID,
                    output_format=settings.ELEVENLABS_OUTPUT_FORMAT,
                    timeout=settings.VOICE_HTTP_TIMEOUT,
                    stability=settings.ELEVENLABS_STABILITY,
                    similarity_boost=settings.ELEVENLABS_SIMILARITY_BOOST,
                ),
                OpenAITTSClient(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL,
                    model=settings.OPENAI_TTS_MODEL,
                    timeout=settings.VOICE_HTTP_TIMEOUT,
                    instructions=settings.OPENAI_TTS_INSTRUCTIONS or None,
                ),
            ],
            storage=FileAudioStorage(settings.AUDIO_STORAGE_PATH),
            voice_registry=VoiceRegistry.from_json(settings.VOICE_REGISTRY_JSON),
            retry_policy=RetryPolicy(
                max_attempts=settings.VOICE_RETRY_ATTEMPTS,
                base_delay_seconds=settings.VOICE_RETRY_BASE_DELAY,
                max_delay_seconds=settings.VOICE_RETRY_MAX_DELAY,
            ),
        )

    async def generate_voice(
        self,
        request: VoiceGenerationRequest,
    ) -> dict[str, str | float]:
        """Generate voiceover audio and return the public contract."""
        result = await self.generate(request)
        return result.to_dict()

    async def generate(self, request: VoiceGenerationRequest) -> VoiceGenerationResult:
        """Generate, store, and measure MP3 audio."""
        text = request.text.strip()
        if not text:
            raise VoiceGenerationError("Voice generation text cannot be empty.")

        voice = self.voice_registry.resolve(request.voice)
        errors: list[str] = []

        for provider_name in request.provider_order:
            provider = self.providers.get(provider_name)
            if provider is None:
                errors.append(f"{provider_name}: provider is not registered")
                continue
            if not provider.is_configured:
                errors.append(f"{provider_name}: provider is not configured")
                continue

            async def synthesize() -> AudioAsset:
                return await provider.synthesize(text=text, voice=voice)

            try:
                asset = await self.retry_policy.run(
                    synthesize, retryable=_is_retryable_voice_error
                )
            except Exception as exc:
                logger.warning("Voice provider %s failed: %s", provider_name, exc)
                errors.append(f"{provider_name}: {exc}")
                continue

            audio_path = await self.storage.save(
                asset.content,
                filename_prefix=request.filename_prefix,
                extension=asset.extension,
            )
            duration = estimate_mp3_duration(asset.content)
            if duration <= 0:
                duration = estimate_spoken_duration(text)
            return VoiceGenerationResult(
                audio_path=audio_path,
                duration=duration,
            )

        raise VoiceGenerationError("All voice providers failed: " + "; ".join(errors))


def _is_retryable_voice_error(exc: Exception) -> bool:
    return isinstance(exc, VoiceProviderError) and exc.retryable
