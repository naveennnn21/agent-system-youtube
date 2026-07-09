"""Database-backed Learning Agent for content strategy improvement."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models import Analytics, Script, Topic, Upload, Video
from app.models.enums import FeedbackType
from app.repositories import AnalyticsRepository, LearningFeedbackRepository
from app.services.learning import (
    ContentPerformanceSample,
    LearningAnalysisRequest,
    LearningAnalysisResult,
    LearningAnalyzer,
    classify_format,
)


class LearningAgentError(RuntimeError):
    """Raised when the learning agent cannot complete a run."""


class LearningAgent:
    """Analyze performance, recommend future content strategy, and store learning."""

    def __init__(
        self,
        *,
        analytics_repository: AnalyticsRepository | None = None,
        learning_repository: LearningFeedbackRepository | None = None,
        analyzer: LearningAnalyzer | None = None,
        default_request: LearningAnalysisRequest | None = None,
    ) -> None:
        self.analytics_repository = analytics_repository
        self.learning_repository = learning_repository
        self.analyzer = analyzer or LearningAnalyzer()
        self.default_request = default_request or LearningAnalysisRequest()

    @classmethod
    def from_session(
        cls,
        session: AsyncSession,
        settings: Settings | None = None,
    ) -> "LearningAgent":
        """Create a production agent from an async database session."""
        settings = settings or get_settings()
        return cls(
            analytics_repository=AnalyticsRepository(session),
            learning_repository=LearningFeedbackRepository(session),
            default_request=LearningAnalysisRequest(
                lookback_days=settings.LEARNING_LOOKBACK_DAYS,
                top_n=settings.LEARNING_TOP_N,
                max_samples=settings.LEARNING_MAX_SAMPLES,
                min_views=settings.LEARNING_MIN_VIEWS,
                store_results=True,
                model_version=settings.LEARNING_MODEL_VERSION,
            ),
        )

    async def learn(
        self,
        request: LearningAnalysisRequest | None = None,
    ) -> dict[str, Any]:
        """Run learning and return the public recommendation payload."""
        result = await self.run_learning_cycle(request)
        return result.to_dict()

    async def run_learning_cycle(
        self,
        request: LearningAnalysisRequest | None = None,
        *,
        samples: list[ContentPerformanceSample] | None = None,
    ) -> LearningAnalysisResult:
        """Analyze historical performance and optionally persist the results."""
        request = request or self.default_request
        if samples is None:
            if self.analytics_repository is None:
                raise LearningAgentError(
                    "analytics_repository is required when samples are not provided."
                )
            analytics_records = (
                await self.analytics_repository.list_recent_with_content(
                    days=request.lookback_days,
                    limit=request.max_samples,
                )
            )
            samples = [sample_from_analytics(record) for record in analytics_records]

        result = self.analyzer.analyze(samples, request)
        if request.store_results and self.learning_repository is not None:
            await self._store_learning_result(result)
        return result

    def recommend_generation_context(
        self,
        result: LearningAnalysisResult,
        *,
        base_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Merge learning hints into a future content-generation context."""
        context = dict(base_context or {})
        context["learning"] = result.recommendations.generation_hints
        context["learning_confidence"] = result.recommendations.confidence
        context["learning_model_version"] = result.model_version
        return context

    async def _store_learning_result(self, result: LearningAnalysisResult) -> None:
        assert self.learning_repository is not None
        feedback_ids: list[str] = []

        aggregate = await self.learning_repository.create(
            feedback_type=FeedbackType.SYSTEM,
            signal="learning_run",
            score=_decimal_score(result.recommendations.confidence),
            notes=(
                f"Analyzed {result.sample_count} eligible videos and identified "
                f"{result.winner_count} winners."
            ),
            recommendations=result.to_dict(),
            model_version=result.model_version,
            reviewed_at=datetime.now(UTC),
        )
        feedback_ids.append(str(aggregate.id))

        for signal in result.winning_hooks[:5]:
            feedback_ids.append(
                await self._store_signal(
                    feedback_type=FeedbackType.QUALITY,
                    signal_name=signal.signal,
                    score=signal.score,
                    payload=signal.to_dict(),
                    model_version=result.model_version,
                )
            )

        for signal in result.winning_topics[:5]:
            feedback_ids.append(
                await self._store_signal(
                    feedback_type=FeedbackType.PERFORMANCE,
                    signal_name=signal.signal,
                    score=signal.score,
                    payload=signal.to_dict(),
                    model_version=result.model_version,
                )
            )

        for signal in result.winning_posting_times[:5]:
            feedback_ids.append(
                await self._store_signal(
                    feedback_type=FeedbackType.AUDIENCE,
                    signal_name=signal.signal,
                    score=signal.score,
                    payload=signal.to_dict(),
                    model_version=result.model_version,
                )
            )

        for signal in result.best_formats[:5]:
            feedback_ids.append(
                await self._store_signal(
                    feedback_type=FeedbackType.QUALITY,
                    signal_name=signal.signal,
                    score=signal.score,
                    payload=signal.to_dict(),
                    model_version=result.model_version,
                )
            )

        result.feedback_ids.extend(feedback_ids)

    async def _store_signal(
        self,
        *,
        feedback_type: FeedbackType,
        signal_name: str,
        score: float,
        payload: dict[str, Any],
        model_version: str,
    ) -> str:
        assert self.learning_repository is not None
        links = _links_from_evidence(payload.get("evidence") or [])
        feedback_data: dict[str, Any] = {
            "feedback_type": feedback_type,
            "signal": signal_name,
            "score": _decimal_score(score),
            "notes": payload.get("recommendation") or "",
            "recommendations": payload,
            "model_version": model_version,
            "reviewed_at": datetime.now(UTC),
        }
        feedback_data.update(links)
        feedback = await self.learning_repository.create(feedback_data)
        return str(feedback.id)


def sample_from_analytics(analytics: Analytics) -> ContentPerformanceSample:
    """Build a learning sample from an analytics snapshot and loaded relations."""
    video: Video = analytics.video
    topic: Topic | None = getattr(video, "topic", None)
    scripts = list(getattr(video, "scripts", []) or [])
    uploads = list(getattr(video, "uploads", []) or [])
    script = _latest_script(scripts)
    upload = _latest_upload(uploads)
    metadata = _merged_metadata(video, script)
    published_at = video.published_at or (upload.uploaded_at if upload else None)
    topic_title = topic.title if topic else video.title
    keywords = list(topic.keywords if topic else [])

    return ContentPerformanceSample(
        video_id=video.id,
        topic_id=topic.id if topic else video.topic_id,
        script_id=script.id if script else None,
        analytics_id=analytics.id,
        title=video.title,
        topic=topic_title,
        hook=(script.hook if script and script.hook else _first_sentence(video.title)),
        keywords=keywords,
        published_at=published_at,
        scheduled_at=video.scheduled_at,
        duration_seconds=video.duration_seconds,
        aspect_ratio=video.aspect_ratio,
        format_label=classify_format(
            duration_seconds=video.duration_seconds,
            aspect_ratio=video.aspect_ratio,
            metadata=metadata,
        ),
        metrics=_analytics_metrics(analytics),
        metadata=metadata,
    )


def _latest_script(scripts: list[Script]) -> Script | None:
    if not scripts:
        return None
    return max(
        scripts,
        key=lambda script: (
            script.version or 0,
            script.created_at or datetime.min.replace(tzinfo=UTC),
        ),
    )


def _latest_upload(uploads: list[Upload]) -> Upload | None:
    if not uploads:
        return None
    return max(
        uploads,
        key=lambda upload: upload.uploaded_at
        or upload.created_at
        or datetime.min.replace(tzinfo=UTC),
    )


def _merged_metadata(video: Video, script: Script | None) -> dict[str, Any]:
    metadata = dict(video.extra_metadata or {})
    if script is not None:
        metadata.update(
            {
                f"script_{key}": value
                for key, value in (script.extra_metadata or {}).items()
            }
        )
    return metadata


def _analytics_metrics(analytics: Analytics) -> dict[str, float]:
    return {
        "views": float(analytics.views or 0),
        "likes": float(analytics.likes or 0),
        "comments": float(analytics.comments or 0),
        "shares": float(analytics.shares or 0),
        "watch_time_seconds": float(analytics.watch_time_seconds or 0),
        "average_view_duration_seconds": _float_or_zero(
            analytics.average_view_duration_seconds
        ),
        "retention_rate": _float_or_zero(analytics.retention_rate),
        "click_through_rate": _float_or_zero(analytics.click_through_rate),
        "subscribers_gained": float(analytics.subscribers_gained or 0),
        "revenue_estimate": _float_or_zero(analytics.revenue_estimate),
    }


def _float_or_zero(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)


def _first_sentence(value: str) -> str:
    return value.split(".")[0].strip()


def _decimal_score(value: float) -> Decimal:
    return Decimal(str(round(float(value), 3)))


def _links_from_evidence(evidence: list[dict[str, Any]]) -> dict[str, uuid.UUID]:
    if not evidence:
        return {}
    first = evidence[0]
    links: dict[str, uuid.UUID] = {}
    for source_key, target_key in (
        ("video_id", "video_id"),
        ("topic_id", "topic_id"),
        ("script_id", "script_id"),
        ("analytics_id", "analytics_id"),
    ):
        value = first.get(source_key)
        if isinstance(value, str) and value:
            links[target_key] = uuid.UUID(value)
    return links
