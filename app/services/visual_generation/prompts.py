"""Image and visual prompt templates."""

from __future__ import annotations

from app.services.visual_generation.models import (
    ImagePrompt,
    SceneSpec,
    VisualGenerationRequest,
)


class VisualPromptBuilder:
    """Create provider-ready image prompts from scene plans."""

    def build(
        self,
        scene: SceneSpec,
        request: VisualGenerationRequest,
    ) -> ImagePrompt:
        keywords = ", ".join(scene.keywords) if scene.keywords else request.topic
        image_prompt = (
            f"{request.style}. Scene {scene.index}: {scene.visual_description} "
            f"Narration context: {scene.narration}. Keywords: {keywords}. "
            f"Compose for {request.aspect_ratio} vertical video, strong foreground "
            "subject, cinematic depth, clean background, no text overlays."
        )
        visual_prompt = (
            f"Scene {scene.index} ({scene.start_seconds}-{scene.end_seconds}s): "
            f"{scene.title}. Camera direction: slow push-in, one clear focal subject, "
            "motion-friendly framing for a YouTube Short."
        )
        return ImagePrompt(
            scene_index=scene.index,
            image_prompt=image_prompt,
            visual_prompt=visual_prompt,
            negative_prompt=request.negative_prompt,
        )
