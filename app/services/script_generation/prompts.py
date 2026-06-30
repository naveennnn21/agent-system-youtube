"""Prompt templates for Claude script generation."""

from __future__ import annotations

import json

from app.services.script_generation.models import ScriptGenerationRequest

SYSTEM_PROMPT = """You are an expert YouTube Shorts script strategist.
Create short-form scripts that maximize retention, curiosity, and viral sharing.

Hard rules:
- Output valid JSON only.
- The JSON object must contain exactly: hook, script, cta.
- Do not include markdown, comments, prefaces, or extra keys.
- The total spoken length must fit 30-60 seconds.
- The hook must create curiosity in the first 1-3 seconds.
- The main script must use short spoken sentences and keep a clear retention loop.
- The CTA must invite sharing, saving, commenting, or following without sounding spammy.
"""

USER_PROMPT_TEMPLATE = """Generate a YouTube Shorts script.

Topic: {topic}
Category: {category}
Keywords: {keywords}
Target length: {target_seconds} seconds
Audience: {audience}
Tone: {tone}
Research context:
{research_context}

Optimization checklist:
- Start with a curiosity gap or surprising contrast.
- Add one open loop that resolves near the end.
- Use concrete language that can be visualized.
- Make the payoff useful enough that viewers might share it.
- Avoid filler, disclaimers, and generic hype.

Return JSON in this exact shape:
{{
  "hook": "...",
  "script": "...",
  "cta": "..."
}}
"""


class ScriptPromptBuilder:
    """Render Claude prompts for script generation."""

    def build(self, request: ScriptGenerationRequest) -> tuple[str, str]:
        """Return ``(system_prompt, user_prompt)``."""
        keywords = ", ".join(request.keywords) if request.keywords else "none"
        research_context = json.dumps(
            request.research_context,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        user_prompt = USER_PROMPT_TEMPLATE.format(
            topic=request.topic,
            category=request.category,
            keywords=keywords,
            target_seconds=request.target_seconds,
            audience=request.audience,
            tone=request.tone,
            research_context=research_context,
        )
        return SYSTEM_PROMPT, user_prompt
