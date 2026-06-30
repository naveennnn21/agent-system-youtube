"""Anthropic Claude client for script generation."""

from __future__ import annotations

import json
from typing import Any

import httpx


class ClaudeConfigurationError(RuntimeError):
    """Raised when Claude is not configured."""


class ClaudeAPIError(RuntimeError):
    """Raised when the Claude API request fails."""


class ClaudeScriptClient:
    """Small async client for Anthropic's Messages API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.anthropic.com",
        anthropic_version: str = "2023-06-01",
        max_tokens: int = 1200,
        timeout: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key.strip()
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.anthropic_version = anthropic_version
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._client = client

    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        """Call Claude and return concatenated text content."""
        if not self.api_key:
            raise ClaudeConfigurationError("ANTHROPIC_API_KEY is required.")

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.anthropic_version,
            "content-type": "application/json",
        }

        try:
            if self._client is not None:
                response = await self._client.post(
                    f"{self.base_url}/v1/messages",
                    headers=headers,
                    json=payload,
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/v1/messages",
                        headers=headers,
                        json=payload,
                    )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = _extract_error_detail(exc.response)
            raise ClaudeAPIError(f"Claude API returned {exc.response.status_code}: {detail}") from exc
        except httpx.HTTPError as exc:
            raise ClaudeAPIError(f"Claude API request failed: {exc}") from exc

        data = response.json()
        return _extract_text(data)


def _extract_text(data: dict[str, Any]) -> str:
    text_blocks: list[str] = []
    for block in data.get("content", []):
        if block.get("type") == "text":
            text_blocks.append(str(block.get("text", "")))
    text = "\n".join(part.strip() for part in text_blocks if part.strip())
    if not text:
        raise ClaudeAPIError("Claude response did not contain text content.")
    return text


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return response.text
    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or error)
    return str(payload)
