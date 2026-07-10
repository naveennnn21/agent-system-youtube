"""YouTube Analytics Agent for collection, storage, and reports."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models import Upload
from app.models.enums import UploadPlatform
from app.repositories import AnalyticsRepository, UploadsRepository
from app.services.analytics import (
    AnalyticsCollectionRequest,
    AnalyticsCollectionResult,
    AnalyticsReporter,
    AnalyticsReport,
    AnalyticsSnapshot,
    StoredAnalyticsSnapshot,
    YouTubeAnalyticsClient,
    YouTubeAnalyticsQuery,
)
from app.services.youtube import GoogleOAuthClient, YouTubeOAuthCredentials


class AnalyticsCollector(Protocol):
    async def fetch_video_metrics(
        self,
        query: YouTubeAnalyticsQuery,
    ) -> list[AnalyticsSnapshot]:
        """Fetch normalized analytics snapshots."""


class AnalyticsAgentError(RuntimeError):
    """Raised when analytics collection cannot proceed."""


class AnalyticsAgent:
    """Collect YouTube metrics, store them in PostgreSQL, and generate reports."""

    def __init__(
        self,
        *,
        collector: AnalyticsCollector | None = None,
        analytics_repository: AnalyticsRepository | None = None,
        uploads_repository: UploadsRepository | None = None,
        reporter: AnalyticsReporter | None = None,
        ids: str = "channel==MINE",
        metrics: list[str] | None = None,
        collection_limit: int = 100,
    ) -> None:
        self.collector = collector
        self.analytics_repository = analytics_repository
        self.uploads_repository = uploads_repository
        self.reporter = reporter or AnalyticsReporter()
        self.ids = ids
        self.metrics = metrics or []
        self.collection_limit = collection_limit

    @classmethod
    def from_session(
        cls,
        session: AsyncSession,
        settings: Settings | None = None,
    ) -> "AnalyticsAgent":
        """Create a production Analytics Agent from a DB session."""
        settings = settings or get_settings()
        credentials = YouTubeOAuthCredentials(
            client_id=settings.YOUTUBE_OAUTH_CLIENT_ID,
            client_secret=settings.YOUTUBE_OAUTH_CLIENT_SECRET,
            refresh_token=settings.YOUTUBE_OAUTH_REFRESH_TOKEN,
            token_uri=settings.YOUTUBE_OAUTH_TOKEN_URI,
            scope=settings.YOUTUBE_ANALYTICS_SCOPE,
        )
        oauth_client = GoogleOAuthClient(
            credentials,
            timeout=settings.YOUTUBE_ANALYTICS_HTTP_TIMEOUT,
        )
        collector = YouTubeAnalyticsClient(
            oauth_client=oauth_client,
            base_url=settings.YOUTUBE_ANALYTICS_BASE_URL,
            timeout=settings.YOUTUBE_ANALYTICS_HTTP_TIMEOUT,
        )
        return cls(
            collector=collector,
            analytics_repository=AnalyticsRepository(session),
            uploads_repository=UploadsRepository(session),
            ids=settings.YOUTUBE_ANALYTICS_IDS,
            metrics=settings.YOUTUBE_ANALYTICS_METRICS,
            collection_limit=settings.YOUTUBE_ANALYTICS_COLLECTION_LIMIT,
        )

    async def collect_metrics(
        self,
        request: AnalyticsCollectionRequest | None = None,
    ) -> dict:
        """Collect metrics and return the public result contract."""
        result = await self.collect(request)
        return result.to_dict()

    async def collect(
        self,
        request: AnalyticsCollectionRequest | None = None,
    ) -> AnalyticsCollectionResult:
        """Fetch YouTube Analytics rows and upsert them into PostgreSQL."""
        request = request or _default_collection_request(
            self.collection_limit, self.metrics
        )
        if self.collector is None:
            raise AnalyticsAgentError("collector is required for analytics collection.")
        if self.analytics_repository is None or self.uploads_repository is None:
            raise AnalyticsAgentError(
                "analytics and uploads repositories are required."
            )

        uploads = await self._uploads_for_collection(request)
        uploads_by_external_id = {
            upload.external_video_id: upload
            for upload in uploads
            if upload.external_video_id
        }
        external_ids = request.external_video_ids or list(uploads_by_external_id)
        if not external_ids:
            return AnalyticsCollectionResult(
                collected_count=0,
                stored_count=0,
                skipped_count=0,
                snapshots=[],
                errors=[
                    "No successful YouTube uploads with external video ids were found."
                ],
            )

        query = YouTubeAnalyticsQuery(
            start_date=request.start_date,
            end_date=request.end_date,
            video_ids=external_ids,
            ids=self.ids,
            metrics=request.metrics or self.metrics,
            dimensions=["video"],
            max_results=request.max_results,
        )
        snapshots = await self.collector.fetch_video_metrics(query)
        stored: list[StoredAnalyticsSnapshot] = []
        skipped = 0
        errors: list[str] = []

        for snapshot in snapshots:
            upload = uploads_by_external_id.get(snapshot.external_video_id)
            if upload is None:
                skipped += 1
                errors.append(
                    f"No upload row found for YouTube video {snapshot.external_video_id}."
                )
                continue
            stored.append(await self._upsert_snapshot(upload, snapshot))

        return AnalyticsCollectionResult(
            collected_count=len(snapshots),
            stored_count=len(stored),
            skipped_count=skipped,
            snapshots=stored,
            errors=errors,
        )

    async def build_report(
        self,
        *,
        start_date: date,
        end_date: date,
        top_n: int = 10,
    ) -> AnalyticsReport:
        """Build an aggregate report from stored PostgreSQL metrics."""
        if self.analytics_repository is None:
            raise AnalyticsAgentError("analytics_repository is required for reporting.")
        records = await self.analytics_repository.list_between(
            start_date=start_date,
            end_date=end_date,
            limit=5000,
        )
        return self.reporter.build_report(
            records,
            start_date=start_date,
            end_date=end_date,
            top_n=top_n,
        )

    async def _uploads_for_collection(
        self,
        request: AnalyticsCollectionRequest,
    ) -> list[Upload]:
        assert self.uploads_repository is not None
        uploads = await self.uploads_repository.list_successful_youtube_uploads(
            limit=request.max_results or self.collection_limit
        )
        if not request.external_video_ids:
            return uploads
        requested = set(request.external_video_ids)
        return [upload for upload in uploads if upload.external_video_id in requested]

    async def _upsert_snapshot(
        self,
        upload: Upload,
        snapshot: AnalyticsSnapshot,
    ) -> StoredAnalyticsSnapshot:
        assert self.analytics_repository is not None
        existing = await self.analytics_repository.get_snapshot(
            upload.video_id,
            snapshot.snapshot_date,
            UploadPlatform.YOUTUBE_SHORTS,
        )
        values: dict[str, Any] = {
            "upload_id": upload.id,
            "views": snapshot.views,
            "likes": snapshot.likes,
            "comments": snapshot.comments,
            "shares": snapshot.shares,
            "watch_time_seconds": snapshot.watch_time_seconds,
            "average_view_duration_seconds": _decimal_or_none(
                snapshot.average_view_duration_seconds
            ),
            "retention_rate": _decimal_or_none(snapshot.retention_rate),
            "click_through_rate": _decimal_or_none(snapshot.click_through_rate),
            "subscribers_gained": snapshot.subscribers_gained,
            "revenue_estimate": _decimal_or_none(snapshot.revenue_estimate),
            "raw_metrics": {
                **snapshot.raw_metrics,
                "external_video_id": snapshot.external_video_id,
            },
        }
        if existing is None:
            record = await self.analytics_repository.create(
                video_id=upload.video_id,
                platform=UploadPlatform.YOUTUBE_SHORTS,
                snapshot_date=snapshot.snapshot_date,
                **values,
            )
            created = True
        else:
            record = await self.analytics_repository.update(existing, **values)
            created = False

        return StoredAnalyticsSnapshot(
            analytics_id=record.id,
            video_id=record.video_id,
            upload_id=record.upload_id,
            external_video_id=snapshot.external_video_id,
            snapshot=snapshot,
            created=created,
        )


def _default_collection_request(
    collection_limit: int,
    metrics: list[str],
) -> AnalyticsCollectionRequest:
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=7)
    return AnalyticsCollectionRequest(
        start_date=start_date,
        end_date=end_date,
        max_results=collection_limit,
        metrics=metrics,
    )


def _decimal_or_none(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(round(float(value), 4)))
