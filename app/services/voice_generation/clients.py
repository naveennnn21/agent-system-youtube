"""HTTP clients for ElevenLabs and OpenAI TTS."""

from __future__ import annotations

from typing import Any

import httpx

from app.services.voice_generation.models import AudioAsset, VoiceProfile


class VoiceProviderError(RuntimeError):
    """Provider failure with retry classification."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class ElevenLabsTTSClient:
    """ElevenLabs text-to-speech provider."""

    provider = "elevenlabs"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.elevenlabs.io",
        model_id: str = "eleven_multilingual_v2",
        output_format: str = "mp3_44100_128",
        timeout: float = 30.0,
        stability: float = 0.45,
        similarity_boost: float = 0.8,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id
        self.output_format = output_format
        self.timeout = timeout
        self.stability = stability
        self.similarity_boost = similarity_boost
        self._client = client

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def synthesize(self, *, text: str, voice: VoiceProfile) -> AudioAsset:
        voice_id = voice.elevenlabs_voice_id
        if not self.api_key or not voice_id:
            raise VoiceProviderError("ElevenLabs voice is not configured.")

        url = f"{self.base_url}/v1/text-to-speech/{voice_id}"
        params = {"output_format": self.output_format}
        headers = {
            "xi-api-key": self.api_key,
            "accept": "audio/mpeg",
            "content-type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": self.stability,
                "similarity_boost": self.similarity_boost,
            },
        }
        response = await _post(
            url,
            params=params,
            headers=headers,
            json=payload,
            timeout=self.timeout,
            client=self._client,
        )
        return AudioAsset(
            content=response.content,
            provider="elevenlabs",
            voice=voice.name,
        )


class OpenAITTSClient:
    """OpenAI text-to-speech fallback provider."""

    provider = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com",
        model: str = "gpt-4o-mini-tts",
        timeout: float = 30.0,
        instructions: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.instructions = instructions
        self._client = client

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def synthesize(self, *, text: str, voice: VoiceProfile) -> AudioAsset:
        openai_voice = voice.openai_voice or "alloy"
        if not self.api_key:
            raise VoiceProviderError("OpenAI API key is not configured.")

        payload: dict[str, Any] = {
            "model": self.model,
            "voice": openai_voice,
            "input": text,
            "response_format": "mp3",
        }
        if self.instructions:
            payload["instructions"] = self.instructions

        response = await _post(
            f"{self.base_url}/v1/audio/speech",
            headers={
                "authorization": f"Bearer {self.api_key}",
                "content-type": "application/json",
            },
            json=payload,
            timeout=self.timeout,
            client=self._client,
        )
        return AudioAsset(
            content=response.content,
            provider="openai",
            voice=voice.name,
        )


async def _post(
    url: str,
    *,
    headers: dict[str, str],
    json: dict[str, Any],
    timeout: float,
    client: httpx.AsyncClient | None,
    params: dict[str, Any] | None = None,
) -> httpx.Response:
    try:
        if client is not None:
            response = await client.post(
                url,
                params=params,
                headers=headers,
                json=json,
            )
        else:
            async with httpx.AsyncClient(timeout=timeout) as http_client:
                response = await http_client.post(
                    url,
                    params=params,
                    headers=headers,
                    json=json,
                )
        response.raise_for_status()
        return response
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        retryable = status_code in {408, 409, 425, 429, 500, 502, 503, 504}
        raise VoiceProviderError(
            f"TTS provider returned HTTP {status_code}: {exc.response.text}",
            retryable=retryable,
        ) from exc
    except httpx.HTTPError as exc:
        raise VoiceProviderError(
            f"TTS provider request failed: {exc}",
            retryable=True,
        ) from exc
