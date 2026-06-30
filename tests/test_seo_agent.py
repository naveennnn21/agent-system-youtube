from __future__ import annotations

import json

import pytest

from app.agents.seo import (
    SEOAgent,
    SEOGenerationError,
    SEOParsingError,
    parse_seo_response,
)
from app.core.config import Settings
from app.schemas.seo import SEOGenerationResponse
from app.services.seo import (
    SEOEvaluator,
    SEOGenerationRequest,
    SEOMetadata,
    SEOPromptBuilder,
)

pytestmark = pytest.mark.no_db


VALID_METADATA = {
    "title": "7 AI Video Editing Secrets That Save Creators Hours",
    "description": (
        "Learn an AI video editing workflow that finds pauses, removes filler, "
        "and creates clear captions for YouTube Shorts. These seven practical "
        "steps help creators edit faster without sacrificing quality. Save this "
        "workflow and try it on your next video."
    ),
    "hashtags": [
        "#AIVideoEditing",
        "#YouTubeShorts",
        "#ContentCreator",
        "#VideoEditing",
    ],
    "keywords": [
        "AI video editing",
        "YouTube Shorts editing",
        "edit videos faster",
        "AI editing workflow",
        "automatic captions",
        "content creator tools",
    ],
}


class FakeSEOProvider:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.system_prompt = ""
        self.user_prompt = ""

    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return json.dumps(self.payload)


def _request() -> SEOGenerationRequest:
    return SEOGenerationRequest(
        topic="AI video editing",
        script={
            "hook": "Most creators waste hours on this edit.",
            "script": "Use AI to remove filler and add accurate captions.",
            "cta": "Save this workflow for your next Short.",
        },
        category="technology",
        seed_keywords=["AI video editing", "YouTube Shorts editing"],
        audience="solo video creators",
        research_context={"trend_score": 91},
    )


def test_prompt_contains_context_and_optimization_constraints() -> None:
    system_prompt, user_prompt = SEOPromptBuilder().build(_request())

    assert "valid JSON only" in system_prompt
    assert "at most 100 characters" in system_prompt
    assert "3-8 relevant hashtags" in system_prompt
    assert "AI video editing" in user_prompt
    assert "solo video creators" in user_prompt
    assert "Most creators waste hours" in user_prompt
    assert '"trend_score": 91' in user_prompt


@pytest.mark.asyncio
async def test_agent_returns_exact_contract_and_high_quality_evaluation() -> None:
    provider = FakeSEOProvider(VALID_METADATA)
    agent = SEOAgent(provider=provider)

    result = await agent.generate(_request())
    public_result = await SEOAgent(
        provider=FakeSEOProvider(VALID_METADATA)
    ).generate_seo(_request())

    assert result.metadata.to_dict() == VALID_METADATA
    assert result.evaluation.is_valid
    assert result.evaluation.ctr_score >= 80
    assert result.evaluation.discoverability_score >= 80
    assert set(public_result) == {"title", "description", "hashtags", "keywords"}
    assert "AI video editing" in provider.user_prompt


def test_parser_normalizes_deduplicates_and_applies_limits() -> None:
    payload = {
        "title": (
            "AI Video Editing: A Very Long Guide for Creators Who Want to "
            "Produce Better YouTube Shorts Without Spending Their Entire Day"
        ),
        "description": "First line.  \n\n Second line.",
        "hashtags": [
            "AI Video Editing",
            "#YouTubeShorts",
            "#aivideoediting",
            "#Creator Tips",
        ],
        "keywords": [
            "AI video editing",
            " ai video editing ",
            "#YouTube Shorts editing",
            "creator workflow",
        ],
    }

    metadata = parse_seo_response(
        "```json\n" + json.dumps(payload) + "\n```",
        title_max_length=70,
        max_hashtags=2,
        max_keywords=2,
    )

    assert len(metadata.title) <= 70
    assert metadata.description == "First line.\nSecond line."
    assert metadata.hashtags == ["#AIVideoEditing", "#YouTubeShorts"]
    assert metadata.keywords == ["AI video editing", "YouTube Shorts editing"]


def test_parser_rejects_missing_or_invalid_fields() -> None:
    with pytest.raises(SEOParsingError, match="missing keys"):
        parse_seo_response('{"title": "Only a title"}')

    invalid = dict(VALID_METADATA)
    invalid["hashtags"] = [123]
    with pytest.raises(SEOParsingError, match="only strings"):
        parse_seo_response(json.dumps(invalid))


def test_evaluator_flags_weak_non_searchable_metadata() -> None:
    evaluation = SEOEvaluator().evaluate(
        SEOMetadata(
            title="A Nice Video",
            description="This is a video.",
            hashtags=["#Video"],
            keywords=["something"],
        ),
        topic="AI video editing",
        seed_keywords=["YouTube Shorts editing"],
    )

    assert not evaluation.is_valid
    assert evaluation.overall_score < 60
    assert "Title does not contain the topic or a seed keyword." in evaluation.issues


@pytest.mark.asyncio
async def test_strict_agent_rejects_metadata_that_fails_evaluation() -> None:
    provider = FakeSEOProvider(
        {
            "title": "A Nice Video",
            "description": "This is a video.",
            "hashtags": ["#Video"],
            "keywords": ["something"],
        }
    )

    with pytest.raises(SEOGenerationError, match="did not pass SEO evaluation"):
        await SEOAgent(provider=provider, strict=True).generate(_request())


def test_from_settings_applies_provider_and_output_limits() -> None:
    settings = Settings(
        ANTHROPIC_API_KEY="test-key",
        SEO_TITLE_MAX_LENGTH=80,
        SEO_DESCRIPTION_MAX_LENGTH=1000,
        SEO_MAX_HASHTAGS=5,
        SEO_MAX_KEYWORDS=10,
        SEO_MIN_OVERALL_SCORE=65,
    )

    agent = SEOAgent.from_settings(settings)

    assert agent.provider.api_key == "test-key"
    assert agent.title_max_length == 80
    assert agent.description_max_length == 1000
    assert agent.max_hashtags == 5
    assert agent.max_keywords == 10
    assert agent.evaluator.minimum_score == 65


def test_public_response_schema_accepts_agent_contract() -> None:
    response = SEOGenerationResponse.model_validate(VALID_METADATA)

    assert response.title == VALID_METADATA["title"]
    assert response.hashtags == VALID_METADATA["hashtags"]
