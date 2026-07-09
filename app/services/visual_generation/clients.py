"""HTTP clients for Flux and Stable Diffusion image APIs."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.services.visual_generation.models import VisualProviderName


class ImageProviderError(RuntimeError):
    """Provider failure with retry classification."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(slots=True)
class GeneratedImage:
    """Raw image returned by a provider."""

    content: bytes
    provider: VisualProviderName
    media_type: str = "image/png"
    metadata: dict[str, Any] = field(default_factory=dict)


class FluxImageClient:
    """Flux/BFL-compatible image provider client."""

    provider: VisualProviderName = "flux"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.bfl.ai",
        generate_endpoint: str = "/v1/flux-pro-1.1",
        result_endpoint: str = "/v1/get_result",
        auth_header: str = "x-key",
        model: str = "flux-pro-1.1",
        timeout: float = 60.0,
        poll_interval_seconds: float = 1.0,
        poll_attempts: int = 30,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.generate_endpoint = generate_endpoint
        self.result_endpoint = result_endpoint
        self.auth_header = auth_header
        self.model = model
        self.timeout = timeout
        self.poll_interval_seconds = poll_interval_seconds
        self.poll_attempts = poll_attempts
        self._client = client

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def generate_image(
        self,
        *,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        aspect_ratio: str,
    ) -> GeneratedImage:
        if not self.api_key:
            raise ImageProviderError("Flux API key is not configured.")

        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "model": self.model,
            "output_format": "png",
        }
        response = await self._request(
            "POST",
            self._url(self.generate_endpoint),
            json=payload,
            headers=self._headers(accept="application/json, image/*"),
        )
        return await self._image_from_response(response)

    async def _image_from_response(self, response: httpx.Response) -> GeneratedImage:
        media_type = response.headers.get("content-type", "image/png").split(";")[0]
        if media_type.startswith("image/"):
            return GeneratedImage(
                content=response.content,
                provider=self.provider,
                media_type=media_type,
            )

        payload = response.json()
        image = await self._image_from_payload(payload)
        image.metadata.update({"raw_response": payload})
        return image

    async def _image_from_payload(self, payload: dict[str, Any]) -> GeneratedImage:
        base64_value = _find_base64_image(payload)
        if base64_value:
            return GeneratedImage(
                content=base64.b64decode(base64_value),
                provider=self.provider,
                media_type="image/png",
            )

        image_url = _find_image_url(payload)
        if image_url:
            response = await self._request("GET", image_url, headers=self._headers())
            media_type = response.headers.get("content-type", "image/png").split(";")[0]
            return GeneratedImage(
                content=response.content,
                provider=self.provider,
                media_type=media_type,
            )

        job_id = payload.get("id") or payload.get("request_id")
        if job_id:
            return await self._poll_result(str(job_id))

        raise ImageProviderError("Flux response did not include image data.")

    async def _poll_result(self, job_id: str) -> GeneratedImage:
        for _ in range(self.poll_attempts):
            response = await self._request(
                "GET",
                self._url(self.result_endpoint),
                params={"id": job_id},
                headers=self._headers(),
            )
            payload = response.json()
            status = str(payload.get("status") or payload.get("state") or "").lower()
            if status in {"ready", "succeeded", "completed", "complete"}:
                image = await self._image_from_payload(payload)
                image.metadata["job_id"] = job_id
                return image
            if status in {"failed", "error", "canceled"}:
                raise ImageProviderError(f"Flux job failed: {payload}")
            await asyncio.sleep(self.poll_interval_seconds)
        raise ImageProviderError("Flux image generation timed out.", retryable=True)

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        try:
            if self._client is not None:
                response = await self._client.request(
                    method,
                    url,
                    headers=headers,
                    json=json,
                    params=params,
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method,
                        url,
                        headers=headers,
                        json=json,
                        params=params,
                    )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            raise _provider_http_error("Flux", exc) from exc
        except httpx.HTTPError as exc:
            raise ImageProviderError(
                f"Flux request failed: {exc}", retryable=True
            ) from exc

    def _headers(self, *, accept: str = "application/json") -> dict[str, str]:
        return {
            self.auth_header: self.api_key,
            "accept": accept,
            "content-type": "application/json",
        }

    def _url(self, endpoint: str) -> str:
        if endpoint.startswith("http"):
            return endpoint
        return f"{self.base_url}/{endpoint.lstrip('/')}"


class StableDiffusionImageClient:
    """Stability/Stable Diffusion image provider client."""

    provider: VisualProviderName = "stable_diffusion"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.stability.ai",
        generate_endpoint: str = "/v2beta/stable-image/generate/core",
        model: str = "stable-image-core",
        timeout: float = 60.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.generate_endpoint = generate_endpoint
        self.model = model
        self.timeout = timeout
        self._client = client

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def generate_image(
        self,
        *,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        aspect_ratio: str,
    ) -> GeneratedImage:
        if not self.api_key:
            raise ImageProviderError("Stable Diffusion API key is not configured.")

        files = {
            "prompt": (None, prompt),
            "negative_prompt": (None, negative_prompt),
            "aspect_ratio": (None, aspect_ratio),
            "output_format": (None, "png"),
            "model": (None, self.model),
        }
        headers = {
            "authorization": f"Bearer {self.api_key}",
            "accept": "image/*, application/json",
        }
        response = await self._post(
            self._url(self.generate_endpoint), files=files, headers=headers
        )
        media_type = response.headers.get("content-type", "image/png").split(";")[0]
        if media_type.startswith("image/"):
            return GeneratedImage(
                content=response.content,
                provider=self.provider,
                media_type=media_type,
            )

        payload = response.json()
        base64_value = _find_base64_image(payload)
        if not base64_value:
            raise ImageProviderError(
                "Stable Diffusion response did not include image data."
            )
        return GeneratedImage(
            content=base64.b64decode(base64_value),
            provider=self.provider,
            media_type="image/png",
            metadata={"raw_response": payload},
        )

    async def _post(
        self,
        url: str,
        *,
        files: dict[str, tuple[None, str]],
        headers: dict[str, str],
    ) -> httpx.Response:
        try:
            if self._client is not None:
                response = await self._client.post(url, files=files, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, files=files, headers=headers)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            raise _provider_http_error("Stable Diffusion", exc) from exc
        except httpx.HTTPError as exc:
            raise ImageProviderError(
                f"Stable Diffusion request failed: {exc}",
                retryable=True,
            ) from exc

    def _url(self, endpoint: str) -> str:
        if endpoint.startswith("http"):
            return endpoint
        return f"{self.base_url}/{endpoint.lstrip('/')}"


def _provider_http_error(
    provider: str, exc: httpx.HTTPStatusError
) -> ImageProviderError:
    status_code = exc.response.status_code
    retryable = status_code in {408, 409, 425, 429, 500, 502, 503, 504}
    return ImageProviderError(
        f"{provider} returned HTTP {status_code}: {exc.response.text}",
        retryable=retryable,
    )


def _find_base64_image(payload: dict[str, Any]) -> str | None:
    candidates = [
        payload.get("image"),
        payload.get("b64_json"),
        payload.get("base64"),
        payload.get("sample"),
    ]
    images = payload.get("images")
    if isinstance(images, list) and images:
        first = images[0]
        if isinstance(first, str):
            candidates.append(first)
        elif isinstance(first, dict):
            candidates.extend(
                [
                    first.get("base64"),
                    first.get("b64_json"),
                    first.get("image"),
                ]
            )
    artifacts = payload.get("artifacts")
    if isinstance(artifacts, list) and artifacts:
        first = artifacts[0]
        if isinstance(first, dict):
            candidates.append(first.get("base64"))

    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return None


def _find_image_url(payload: dict[str, Any]) -> str | None:
    for key in ("url", "image_url", "output_url"):
        value = payload.get(key)
        if isinstance(value, str) and value.startswith("http"):
            return value
    result = payload.get("result")
    if isinstance(result, dict):
        return _find_image_url(result)
    return None
