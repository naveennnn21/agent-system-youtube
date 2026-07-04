from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.agents.learning import LearningAgent, sample_from_analytics
from app.models import Analytics, Script, Topic, Upload, Video
from app.models.enums import FeedbackType
from app.schemas.learning import LearningAnalysisResponse
from app.services.learning import (
    ContentPerformanceSample,
    LearningAnalysisRequest,
    LearningAnalyzer,
    classify_format,
    hook_pattern,
)

pytestmark = pytest.mark.no_db


class FakeLearningRepository:
    def __init__(self) -> None:
        self.created: list[SimpleNamespace] = []

    async def create(self, **values):
        feedback = SimpleNamespace(id=uuid.uuid4(), **values)
        self.created.append(feedback)
        return feedback


def _sample(
    *,
    title: str,
    topic: str,
    hook: str,
    views: int,
    likes: int,
    comments: int,
    shares: int,
    retention: float,
    ctr: float,
    published_at: datetime,
    duration_seconds: int = 35,
    keywords: list[str] | None = None,
    format_label: str = "fast_cut_vertical",
) -> ContentPerformanceSample:
    return ContentPerformanceSample(
        video_id=uuid.uuid4(),
        topic_id=uuid.uuid4(),
        script_id=uuid.uuid4(),
        analytics_id=uuid.uuid4(),
        title=title,
        topic=topic,
        hook=hook,
        keywords=keywords or [topic.lower(), "youtube shorts"],
        published_at=published_at,
        scheduled_at=None,
        duration_seconds=duration_seconds,
        aspect_ratio="9:16",
        format_label=format_label,
        metrics={
            "views": float(views),
            "likes": float(likes),
            "comments": float(comments),
            "shares": float(shares),
            "watch_time_seconds": float(views * 20),
            "average_view_duration_seconds": duration_seconds * retention,
            "retention_rate": retention,
            "click_through_rate": ctr,
            "subscribers_gained": float(max(1, views // 1000)),
            "revenue_estimate": 0.0,
        },
    )


def _samples() -> list[ContentPerformanceSample]:
    return [
        _sample(
            title="7 AI Editing Tricks That Save Hours",
            topic="AI video editing",
            hook="7 AI editing tricks that save creators hours",
            views=15000,
            likes=900,
            comments=120,
            shares=180,
            retention=0.82,
            ctr=0.13,
            published_at=datetime(2026, 7, 7, 14, 0, tzinfo=UTC),
            keywords=["AI video editing", "creator workflow"],
        ),
        _sample(
            title="What if your Short could edit itself?",
            topic="AI video editing",
            hook="What if your Short could edit itself?",
            views=12000,
            likes=720,
            comments=95,
            shares=160,
            retention=0.78,
            ctr=0.11,
            published_at=datetime(2026, 7, 7, 14, 30, tzinfo=UTC),
            keywords=["AI video editing", "automatic captions"],
        ),
        _sample(
            title="A generic productivity tip",
            topic="Productivity",
            hook="Here is a productivity tip",
            views=500,
            likes=20,
            comments=1,
            shares=2,
            retention=0.35,
            ctr=0.03,
            published_at=datetime(2026, 7, 8, 8, 0, tzinfo=UTC),
            format_label="standard_short_vertical",
        ),
    ]


def test_learning_analyzer_finds_winners_and_generation_hints() -> None:
    result = LearningAnalyzer().analyze(
        _samples(),
        LearningAnalysisRequest(top_n=2, min_views=0, model_version="test-v1"),
    )

    assert result.sample_count == 3
    assert result.winner_count == 2
    assert result.top_videos[0].sample.topic == "AI video editing"
    assert result.winning_topics[0].value == "AI video editing"
    assert result.winning_topics[0].count == 2
    assert {hook.value for hook in result.winning_hooks} == {
        "numbered_payoff",
        "curiosity_question",
    }
    assert result.winning_posting_times[0].value == "Tuesday 14:00 UTC"
    assert result.best_formats[0].value == "fast_cut_vertical"
    assert result.recommendations.generation_hints["preferred_topics"] == [
        "AI video editing"
    ]
    assert "AI video editing" in result.recommendations.generation_hints["preferred_keywords"]


def test_empty_learning_result_keeps_safe_defaults() -> None:
    result = LearningAnalyzer().analyze([], LearningAnalysisRequest())

    assert result.sample_count == 0
    assert result.winner_count == 0
    assert result.recommendations.format_defaults["duration_seconds"] == 45
    assert result.recommendations.confidence == 0


def test_hook_and_format_classification_are_stable() -> None:
    assert hook_pattern("3 mistakes creators make") == "numbered_payoff"
    assert hook_pattern("What if editing took one minute?") == "curiosity_question"
    assert hook_pattern("Stop making this caption mistake") == "mistake_warning"
    assert classify_format(duration_seconds=30, aspect_ratio="9:16") == "fast_cut_vertical"
    assert classify_format(
        duration_seconds=55,
        aspect_ratio="9:16",
        metadata={"format": "Talking Head Explainer"},
    ) == "talking_head_explainer"


@pytest.mark.asyncio
async def test_learning_agent_stores_aggregate_and_signal_feedback() -> None:
    repository = FakeLearningRepository()
    agent = LearningAgent(learning_repository=repository)

    result = await agent.run_learning_cycle(
        LearningAnalysisRequest(top_n=2, min_views=0, store_results=True),
        samples=_samples(),
    )

    assert result.feedback_ids
    assert repository.created[0].signal == "learning_run"
    assert repository.created[0].feedback_type == FeedbackType.SYSTEM
    signals = {feedback.signal for feedback in repository.created}
    assert "winning_hook" in signals
    assert "winning_topic" in signals
    assert "winning_posting_time" in signals
    assert "best_format" in signals
    assert all(feedback.model_version == "learning-agent-v1" for feedback in repository.created)


def test_learning_agent_merges_generation_context() -> None:
    result = LearningAnalyzer().analyze(
        _samples(),
        LearningAnalysisRequest(top_n=2, min_views=0),
    )
    context = LearningAgent().recommend_generation_context(
        result,
        base_context={"audience": "solo creators"},
    )

    assert context["audience"] == "solo creators"
    assert context["learning"]["preferred_topics"] == ["AI video editing"]
    assert context["learning_confidence"] > 0


def test_sample_from_analytics_uses_related_video_topic_script_and_upload() -> None:
    topic = Topic(
        id=uuid.uuid4(),
        title="AI video editing",
        keywords=["AI video editing", "creator workflow"],
    )
    video = Video(
        id=uuid.uuid4(),
        title="7 AI Editing Tricks",
        topic=topic,
        duration_seconds=34,
        aspect_ratio="9:16",
        extra_metadata={"format": "Fast Cut"},
    )
    script = Script(
        id=uuid.uuid4(),
        video=video,
        topic=topic,
        version=2,
        hook="7 AI editing tricks that save creators hours",
        full_text="Full script",
        extra_metadata={"prompt_style": "curiosity"},
    )
    upload = Upload(
        id=uuid.uuid4(),
        video=video,
        uploaded_at=datetime(2026, 7, 7, 14, 0, tzinfo=UTC),
    )
    video.scripts = [script]
    video.uploads = [upload]
    analytics = Analytics(
        id=uuid.uuid4(),
        video=video,
        snapshot_date=date(2026, 7, 8),
        views=1000,
        likes=80,
        comments=10,
        shares=20,
        watch_time_seconds=30000,
        average_view_duration_seconds=Decimal("30.5"),
        retention_rate=Decimal("0.8200"),
        click_through_rate=Decimal("0.1200"),
        subscribers_gained=5,
    )

    sample = sample_from_analytics(analytics)

    assert sample.video_id == video.id
    assert sample.topic == "AI video editing"
    assert sample.hook == "7 AI editing tricks that save creators hours"
    assert sample.keywords == ["AI video editing", "creator workflow"]
    assert sample.format_label == "fast_cut"
    assert sample.published_at == upload.uploaded_at
    assert sample.metrics["retention_rate"] == 0.82


def test_public_learning_schema_accepts_result_contract() -> None:
    result = LearningAnalyzer().analyze(
        _samples(),
        LearningAnalysisRequest(top_n=2, min_views=0),
    )

    response = LearningAnalysisResponse.model_validate(result.to_dict())

    assert response.sample_count == 3
    assert response.recommendations["generation_hints"]["preferred_topics"] == [
        "AI video editing"
    ]
