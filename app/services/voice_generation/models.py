"""Data models for voice generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

VoiceProviderName = Literal["elevenlabs", "openai"]


@dataclass(slots=True)
class VoiceProfile:
    """Provider-specific IDs for one logical voice."""

    name: str
    elevenlabs_voice_id: str | None = None
    openai_voice: str | None = None
    description: str = ""


@dataclass(slots=True)
class VoiceGenerationRequest:
    """Input for text-to-speech generation."""

    text: str
    voice: str = "narrator"
    filename_prefix: str = "voiceover"
    provider_order: list[VoiceProviderName] = field(
        default_factory=lambda: ["elevenlabs", "openai"]
    )
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AudioAsset:
    """Raw audio returned by a provider."""

    content: bytes
    provider: VoiceProviderName
    voice: str
    extension: str = "mp3"
    media_type: str = "audio/mpeg"


@dataclass(slots=True)
class VoiceGenerationResult:
    """Public voice generation output contract."""

    audio_path: str
    duration: float

    def to_dict(self) -> dict[str, str | float]:
        return {
            "audio_path": self.audio_path,
            "duration": self.duration,
        }
