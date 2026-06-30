from __future__ import annotations

import base64
from pathlib import Path

import httpx
import pytest

from app.agents.visual_generation import VisualGenerationAgent, VisualGenerationError
from app.services.visual_generation import (
    FileVisualStorage,
    FluxImageClient,
    GeneratedImage,
    ImageProviderError,
    SceneBreakdownGenerator,
    StableDiffusionImageClient,
    VisualGenerationRequest,
    VisualPromptBuilder,
)
from app.services.visual_generation.retry import RetryPolicy

pytestmark = pytest.mark.no_db


class FakeImageProvider:
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

    async def generate_image(
        self,
        *,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        aspect_ratio: str,
    ) -> GeneratedImage:
        self.calls += 1
        if self.failures > 0:
            self.failures -= 1
            raise ImageProviderError("temporary image outage", retryable=self.retryable)
        return GeneratedImage(
            content=self.content,
            provider=self.provider,
            media_type="image/png",
            metadata={"width_request": width, "height_request": height},
        )


def png_bytes(width: int = 4, height: int = 7) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
        + b"\x00\x00\x00\x00"
    )


def script_text() -> str:
    return (
        "What if your next video only needs one visual idea? "
        "First, show the problem clearly with a simple before-and-after. "
        "Then zoom into the detail people usually miss. "
        "Finally, reveal the payoff in a clean cinematic shot. "
        "Save this sequence for your next short."
    )


def test_scene_breakdown_generates_timed_scenes() -> None:
    request = VisualGenerationRequest(
        script=script_text(),
        topic="creator visuals",
        max_scenes=4,
    )

    scenes = SceneBreakdownGenerator().generate(request)

    assert 1 <= len(scenes) <= 4
    assert scenes[0].index == 1
    assert scenes[0].start_seconds == 0
    assert scenes[-1].end_seconds >= 30
    assert "creator visuals" in scenes[0].visual_description
    assert scenes[0].keywords


def test_prompt_builder_creates_image_and_visual_prompts() -> None:
    request = VisualGenerationRequest(
        script=script_text(),
        topic="creator visuals",
        style="cinematic neon editorial",
    )
    scene = SceneBreakdownGenerator().generate(request)[0]

    prompt = VisualPromptBuilder().build(scene, request)

    assert prompt.scene_index == scene.index
    assert "cinematic neon editorial" in prompt.image_prompt
    assert "9:16" in prompt.image_prompt
    assert "Camera direction" in prompt.visual_prompt
    assert "low quality" in prompt.negative_prompt


@pytest.mark.asyncio
async def test_flux_client_posts_payload_and_extracts_image_bytes() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = request.headers["x-key"]
        captured["payload"] = request.read()
        return httpx.Response(200, content=png_bytes(), headers={"content-type": "image/png"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = FluxImageClient(api_key="flux-key", client=client)
        image = await provider.generate_image(
            prompt="vertical cinematic creator workspace",
            negative_prompt="blurry",
            width=1024,
            height=1792,
            aspect_ratio="9:16",
        )

    assert captured["url"] == "https://api.bfl.ai/v1/flux-pro-1.1"
    assert captured["api_key"] == "flux-key"
    assert b"vertical cinematic creator workspace" in captured["payload"]
    assert image.provider == "flux"
    assert image.content.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_flux_client_polls_async_job_and_decodes_base64() -> None:
    calls: list[str] = []
    encoded = base64.b64encode(png_bytes(width=8, height=9)).decode()

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.method == "POST":
            return httpx.Response(200, json={"id": "job-1"})
        return httpx.Response(200, json={"status": "Ready", "image": encoded})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = FluxImageClient(
            api_key="flux-key",
            poll_interval_seconds=0,
            client=client,
        )
        image = await provider.generate_image(
            prompt="scene",
            negative_prompt="bad",
            width=1024,
            height=1792,
            aspect_ratio="9:16",
        )

    assert any("/v1/get_result" in call for call in calls)
    assert image.metadata["job_id"] == "job-1"
    assert image.content.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_stable_diffusion_client_posts_multipart_and_extracts_image() -> None:
    captured: dict[str, object] = {}
    encoded = base64.b64encode(png_bytes()).decode()

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["authorization"]
        body = request.read()
        captured["body"] = body
        return httpx.Response(200, json={"image": encoded})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = StableDiffusionImageClient(api_key="stability-key", client=client)
        image = await provider.generate_image(
            prompt="vertical scene",
            negative_prompt="bad",
            width=1024,
            height=1792,
            aspect_ratio="9:16",
        )

    assert captured["url"] == (
        "https://api.stability.ai/v2beta/stable-image/generate/core"
    )
    assert captured["authorization"] == "Bearer stability-key"
    assert b"vertical scene" in captured["body"]
    assert b"output_format" in captured["body"]
    assert image.provider == "stable_diffusion"
    assert image.content.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_visual_agent_retries_and_stores_assets(tmp_path) -> None:
    primary = FakeImageProvider(
        provider="flux",
        content=png_bytes(width=10, height=20),
        failures=1,
        retryable=True,
    )
    agent = VisualGenerationAgent(
        providers=[primary],
        storage=FileVisualStorage(tmp_path),
        retry_policy=RetryPolicy(max_attempts=2, base_delay_seconds=0),
    )

    result = await agent.generate(
        VisualGenerationRequest(
            script=script_text(),
            topic="creator visuals",
            max_scenes=2,
            filename_prefix="visual test",
        )
    )
    payload = result.to_dict()

    assert primary.calls >= 2
    assert len(payload["scenes"]) == 2
    assert len(payload["prompts"]) == 2
    assert len(payload["assets"]) == 2
    assert payload["assets"][0]["width"] == 10
    assert payload["assets"][0]["height"] == 20
    assert Path(payload["assets"][0]["asset_path"]).exists()


@pytest.mark.asyncio
async def test_visual_agent_falls_back_to_stable_diffusion(tmp_path) -> None:
    primary = FakeImageProvider(
        provider="flux",
        content=b"",
        failures=1,
        retryable=False,
    )
    fallback = FakeImageProvider(
        provider="stable_diffusion",
        content=png_bytes(width=3, height=5),
    )
    agent = VisualGenerationAgent(
        providers=[primary, fallback],
        storage=FileVisualStorage(tmp_path),
        retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=0),
    )

    result = await agent.generate(
        VisualGenerationRequest(
            script=script_text(),
            provider_order=["flux", "stable_diffusion"],
            max_scenes=1,
        )
    )

    assert primary.calls == 1
    assert fallback.calls == 1
    assert result.assets[0].provider == "stable_diffusion"


@pytest.mark.asyncio
async def test_visual_agent_reports_all_provider_failures(tmp_path) -> None:
    agent = VisualGenerationAgent(
        providers=[
            FakeImageProvider(provider="flux", content=b"", configured=False),
            FakeImageProvider(
                provider="stable_diffusion",
                content=b"",
                configured=False,
            ),
        ],
        storage=FileVisualStorage(tmp_path),
        retry_policy=RetryPolicy(max_attempts=1, base_delay_seconds=0),
    )

    with pytest.raises(VisualGenerationError, match="All image providers failed"):
        await agent.generate(VisualGenerationRequest(script=script_text(), max_scenes=1))
