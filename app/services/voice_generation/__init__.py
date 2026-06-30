"""Voice generation service package."""

from app.services.voice_generation.clients import (
    ElevenLabsTTSClient,
    OpenAITTSClient,
    VoiceProviderError,
)
from app.services.voice_generation.duration import estimate_mp3_duration
from app.services.voice_generation.models import (
    AudioAsset,
    VoiceGenerationRequest,
    VoiceGenerationResult,
    VoiceProfile,
)
from app.services.voice_generation.retry import RetryPolicy
from app.services.voice_generation.storage import FileAudioStorage
from app.services.voice_generation.voices import VoiceRegistry

__all__ = [
    "AudioAsset",
    "ElevenLabsTTSClient",
    "FileAudioStorage",
    "OpenAITTSClient",
    "RetryPolicy",
    "VoiceGenerationRequest",
    "VoiceGenerationResult",
    "VoiceProviderError",
    "VoiceProfile",
    "VoiceRegistry",
    "estimate_mp3_duration",
]
