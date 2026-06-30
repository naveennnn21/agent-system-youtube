"""Data models for visual generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

VisualProviderName = Literal["flux", "stable_diffusion"]


@dataclass(slots=True)
class VisualGenerationRequest:
    """Input for visual generation from a script."""

    script: str | dict[str, str]
    topic: str = "YouTube Shorts"
    style: str = "cinematic, high-retention, vertical short-form video"
    aspect_ratio: str = "9:16"
    width: int = 1024
    height: int = 1792
    max_scenes: int = 6
    filename_prefix: str = "visual"
    negative_prompt: str = (
        "low quality, blurry, distorted text, watermark, logo, extra fingers, "
        "bad anatomy, unreadable captions"
    )
    provider_order: list[VisualProviderName] = field(
        default_factory=lambda: ["flux", "stable_diffusion"]
    )
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SceneSpec:
    """Scene-level visual plan."""

    index: int
    title: str
    narration: str
    start_seconds: float
    end_seconds: float
    visual_description: str
    keywords: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "title": self.title,
            "narration": self.narration,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "visual_description": self.visual_description,
            "keywords": self.keywords,
        }


@dataclass(slots=True)
class ImagePrompt:
    """Prompt pair for one visual asset."""

    scene_index: int
    image_prompt: str
    visual_prompt: str
    negative_prompt: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_index": self.scene_index,
            "image_prompt": self.image_prompt,
            "visual_prompt": self.visual_prompt,
            "negative_prompt": self.negative_prompt,
        }


@dataclass(slots=True)
class VisualAsset:
    """Stored visual asset metadata."""

    scene_index: int
    asset_path: str
    provider: VisualProviderName
    prompt: str
    width: int | None
    height: int | None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_index": self.scene_index,
            "asset_path": self.asset_path,
            "provider": self.provider,
            "prompt": self.prompt,
            "width": self.width,
            "height": self.height,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class VisualGenerationResult:
    """Public visual generation output contract."""

    scenes: list[SceneSpec]
    prompts: list[ImagePrompt]
    assets: list[VisualAsset]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenes": [scene.to_dict() for scene in self.scenes],
            "prompts": [prompt.to_dict() for prompt in self.prompts],
            "assets": [asset.to_dict() for asset in self.assets],
        }
