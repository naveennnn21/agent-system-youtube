# SEO Agent

`SEOAgent` generates YouTube Shorts packaging metadata from a topic, script,
research context, and optional seed keywords. Claude is the production provider;
tests and other callers can inject any async provider implementing
`generate_text(system_prompt=..., user_prompt=...)`.

## Usage

```python
from app.agents.seo import SEOAgent
from app.services.seo import SEOGenerationRequest

agent = SEOAgent.from_settings()
metadata = await agent.generate_seo(
    SEOGenerationRequest(
        topic="AI video editing",
        script={
            "hook": "Most creators waste hours on this edit.",
            "script": "Use AI to find pauses, cut filler, and add captions.",
            "cta": "Save this workflow for your next Short.",
        },
        category="technology",
        seed_keywords=["AI video editing", "YouTube Shorts editing"],
    )
)
```

The public result always has this shape:

```json
{
  "title": "7 AI Video Editing Tricks That Save Hours",
  "description": "Learn a faster AI video editing workflow...",
  "hashtags": ["#AIVideoEditing", "#YouTubeShorts"],
  "keywords": ["AI video editing", "YouTube Shorts editing"]
}
```

`generate()` additionally returns deterministic CTR, discoverability,
description, and overall scores. Set `strict=True` when constructing the agent
to reject metadata that does not pass those checks.

## Configuration

- `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, and existing Anthropic HTTP settings
- `SEO_TITLE_MAX_LENGTH`
- `SEO_DESCRIPTION_MAX_LENGTH`
- `SEO_MAX_HASHTAGS`
- `SEO_MAX_KEYWORDS`
- `SEO_MIN_OVERALL_SCORE`
