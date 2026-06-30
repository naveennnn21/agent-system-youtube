"""Prompt templates for YouTube SEO metadata generation."""

from __future__ import annotations

import json

from app.services.seo.models import SEOGenerationRequest


SYSTEM_PROMPT = """You are a YouTube Shorts SEO and packaging strategist.
Generate accurate metadata that improves qualified clicks and search discovery.

Hard rules:
- Output valid JSON only, with exactly: title, description, hashtags, keywords.
- hashtags and keywords must be JSON arrays of strings.
- The title must be compelling, specific, natural, and at most 100 characters.
- Lead with the strongest searchable idea; never use misleading clickbait.
- The description must summarize the payoff and naturally include primary keywords.
- Include a concise viewer action in the description.
- Return 3-8 relevant hashtags and 5-20 relevant keyword phrases.
- Do not repeat phrases, stuff keywords, use unsupported claims, or add markdown.
"""


USER_PROMPT_TEMPLATE = """Create YouTube Shorts metadata for this content.

Topic: {topic}
Category: {category}
Audience: {audience}
Language: {language}
Channel: {channel_name}
Seed keywords: {seed_keywords}

Script:
<script>
{script}
</script>

Research context:
{research_context}

Optimization goals:
- Make the title clear enough to understand instantly and intriguing enough to click.
- Match the title and description to the actual script payoff.
- Put the primary search phrase in the title and opening description naturally.
- Mix broad discovery terms with specific long-tail keyword phrases.
- Prefer concrete benefits, contrasts, questions, or numbers when truthful.

Return this exact JSON shape:
{{
  "title": "...",
  "description": "...",
  "hashtags": ["#Example", "#YouTubeShorts"],
  "keywords": ["primary phrase", "specific long-tail phrase"]
}}
"""


class SEOPromptBuilder:
    """Render model prompts for metadata generation."""

    def build(self, request: SEOGenerationRequest) -> tuple[str, str]:
        topic = request.topic.strip()
        if not topic:
            raise ValueError("SEO topic cannot be empty.")

        script = _script_text(request.script)
        if not script:
            raise ValueError("SEO script cannot be empty.")

        user_prompt = USER_PROMPT_TEMPLATE.format(
            topic=topic,
            category=request.category.strip() or "general",
            audience=request.audience.strip() or "curious general viewers",
            language=request.language.strip() or "English",
            channel_name=request.channel_name.strip() or "not provided",
            seed_keywords=", ".join(request.seed_keywords) or "none",
            script=script,
            research_context=json.dumps(
                request.research_context,
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            ),
        )
        return SYSTEM_PROMPT, user_prompt


def _script_text(script: str | dict[str, str]) -> str:
    if isinstance(script, str):
        return " ".join(script.split())
    if not isinstance(script, dict):
        raise ValueError("SEO script must be a string or a script mapping.")
    return " ".join(
        value.strip()
        for key in ("hook", "script", "cta")
        if isinstance((value := script.get(key)), str) and value.strip()
    )
