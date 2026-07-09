"""Visual Generation Agent using Flux primary and Stable Diffusion fallback."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Protocol

from app.core.config import Settings, get_settings
from app.services.visual_generation import (
    FileVisualStorage,
    FluxImageClient,
    GeneratedImage,
    ImageProviderError,
    SceneBreakdownGenerator,
    StableDiffusionImageClient,
    VisualAsset,
    VisualGenerationRequest,
    VisualGenerationResult,
    VisualPromptBuilder,
)
from app.services.visual_generation.models import VisualProviderName
from app.services.visual_generation.retry import RetryPolicy
from app.services.visual_generation.storage import extension_from_media_type

logger = logging.getLogger(__name__)


class VisualGenerationError(RuntimeError):
    """Raised when visual generation cannot complete."""


class ImageProvider(Protocol):
    provider: VisualProviderName

    @property
    def is_configured(self) -> bool:
        """Return whether this provider can be used."""

    async def generate_image(
        self,
        *,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        aspect_ratio: str,
    ) -> GeneratedImage:
        """Generate an image for one scene prompt."""


class VisualGenerationAgent:
    """Generate scene breakdowns, prompts, and stored image assets."""

    def __init__(
        self,
        *,
        providers: Iterable[ImageProvider],
        storage: FileVisualStorage,
        scene_generator: SceneBreakdownGenerator | None = None,
        prompt_builder: VisualPromptBuilder | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.providers = {provider.provider: provider for provider in providers}
        self.storage = storage
        self.scene_generator = scene_generator or SceneBreakdownGenerator()
        self.prompt_builder = prompt_builder or VisualPromptBuilder()
        self.retry_policy = retry_policy or RetryPolicy()

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "VisualGenerationAgent":
        """Create the production visual agent from application settings."""
        settings = settings or get_settings()
        return cls(
            providers=[
                FluxImageClient(
                    api_key=settings.FLUX_API_KEY,
                    base_url=settings.FLUX_BASE_URL,
                    generate_endpoint=settings.FLUX_GENERATE_ENDPOINT,
                    result_endpoint=settings.FLUX_RESULT_ENDPOINT,
                    auth_header=settings.FLUX_AUTH_HEADER,
                    model=settings.FLUX_MODEL,
                    timeout=settings.VISUAL_HTTP_TIMEOUT,
                    poll_interval_seconds=settings.FLUX_POLL_INTERVAL,
                    poll_attempts=settings.FLUX_POLL_ATTEMPTS,
                ),
                StableDiffusionImageClient(
                    api_key=settings.STABILITY_API_KEY,
                    base_url=settings.STABILITY_BASE_URL,
                    generate_endpoint=settings.STABILITY_GENERATE_ENDPOINT,
                    model=settings.STABILITY_MODEL,
                    timeout=settings.VISUAL_HTTP_TIMEOUT,
                ),
            ],
            storage=FileVisualStorage(settings.VISUAL_STORAGE_PATH),
            retry_policy=RetryPolicy(
                max_attempts=settings.VISUAL_RETRY_ATTEMPTS,
                base_delay_seconds=settings.VISUAL_RETRY_BASE_DELAY,
                max_delay_seconds=settings.VISUAL_RETRY_MAX_DELAY,
            ),
        )

    async def generate_visuals(
        self,
        request: VisualGenerationRequest,
    ) -> dict:
        """Generate visuals and return the public contract."""
        result = await self.generate(request)
        return result.to_dict()

    async def generate(
        self, request: VisualGenerationRequest
    ) -> VisualGenerationResult:
        """Generate scene breakdown, prompts, and stored image assets."""
        scenes = self.scene_generator.generate(request)
        prompts = [self.prompt_builder.build(scene, request) for scene in scenes]
        assets: list[VisualAsset] = []

        for prompt in prompts:
            image, provider_name = await self._generate_image(
                request, prompt.image_prompt, prompt.negative_prompt
            )
            extension = extension_from_media_type(image.media_type)
            path, width, height = await self.storage.save(
                image.content,
                filename_prefix=f"{request.filename_prefix}-scene-{prompt.scene_index}",
                extension=extension,
            )
            assets.append(
                VisualAsset(
                    scene_index=prompt.scene_index,
                    asset_path=path,
                    provider=provider_name,
                    prompt=prompt.image_prompt,
                    width=width,
                    height=height,
                    metadata=image.metadata,
                )
            )

        return VisualGenerationResult(scenes=scenes, prompts=prompts, assets=assets)

    async def _generate_image(
        self,
        request: VisualGenerationRequest,
        prompt: str,
        negative_prompt: str,
    ) -> tuple[GeneratedImage, VisualProviderName]:
        errors: list[str] = []

        for provider_name in request.provider_order:
            provider = self.providers.get(provider_name)
            if provider is None:
                errors.append(f"{provider_name}: provider is not registered")
                continue
            if not provider.is_configured:
                errors.append(f"{provider_name}: provider is not configured")
                continue

            async def generate_image() -> GeneratedImage:
                return await provider.generate_image(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=request.width,
                    height=request.height,
                    aspect_ratio=request.aspect_ratio,
                )

            try:
                image = await self.retry_policy.run(
                    generate_image, retryable=_is_retryable_image_error
                )
                return image, provider_name
            except Exception as exc:
                logger.warning("Image provider %s failed: %s", provider_name, exc)
                errors.append(f"{provider_name}: {exc}")

        raise VisualGenerationError("All image providers failed: " + "; ".join(errors))


def _is_retryable_image_error(exc: Exception) -> bool:
    return isinstance(exc, ImageProviderError) and exc.retryable
