"""Voice registry and provider voice mapping."""

from __future__ import annotations

import json
from typing import Any

from app.services.voice_generation.models import VoiceProfile

DEFAULT_VOICES: dict[str, VoiceProfile] = {
    "narrator": VoiceProfile(
        name="narrator",
        elevenlabs_voice_id="21m00Tcm4TlvDq8ikWAM",
        openai_voice="alloy",
        description="Balanced neutral narrator.",
    ),
    "warm": VoiceProfile(
        name="warm",
        elevenlabs_voice_id="EXAVITQu4vr4xnSDxMaL",
        openai_voice="nova",
        description="Warm and personable voice.",
    ),
    "energetic": VoiceProfile(
        name="energetic",
        elevenlabs_voice_id="pNInz6obpgDQGcFmaJgB",
        openai_voice="echo",
        description="Energetic short-form presenter.",
    ),
}


class VoiceRegistry:
    """Resolve logical voice names to provider-specific voice IDs."""

    def __init__(self, voices: dict[str, VoiceProfile] | None = None) -> None:
        self._voices = voices or DEFAULT_VOICES.copy()

    @classmethod
    def from_json(cls, raw_json: str | None) -> "VoiceRegistry":
        """Create a registry from optional JSON configuration."""
        registry = cls()
        if not raw_json:
            return registry

        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ValueError("VOICE_REGISTRY_JSON must be valid JSON.") from exc

        if not isinstance(payload, dict):
            raise ValueError("VOICE_REGISTRY_JSON must be a JSON object.")

        for name, config in payload.items():
            if not isinstance(config, dict):
                raise ValueError("Each voice registry entry must be a JSON object.")
            registry.register(
                VoiceProfile(
                    name=str(name),
                    elevenlabs_voice_id=_optional_str(
                        config.get("elevenlabs_voice_id")
                    ),
                    openai_voice=_optional_str(config.get("openai_voice")),
                    description=str(config.get("description") or ""),
                )
            )
        return registry

    def register(self, profile: VoiceProfile) -> None:
        self._voices[profile.name] = profile

    def resolve(self, voice: str) -> VoiceProfile:
        try:
            return self._voices[voice]
        except KeyError as exc:
            known = ", ".join(sorted(self._voices))
            raise ValueError(
                f"Unknown voice '{voice}'. Available voices: {known}"
            ) from exc

    def all(self) -> list[VoiceProfile]:
        return list(self._voices.values())


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
