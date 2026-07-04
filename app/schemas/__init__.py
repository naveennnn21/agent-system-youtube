"""Pydantic request and response schemas."""

from app.schemas.analytics import (
    AnalyticsCollectionResponse,
    AnalyticsMetricResponse,
    AnalyticsReportResponse,
)
from app.schemas.automation import (
    DailyShortsScheduleResponse,
    EnqueuedTaskResponse,
    PurgeQueueResponse,
    QueueInspectionResponse,
    RevokeTaskResponse,
    TaskStatusResponse,
)
from app.schemas.dashboard import (
    DashboardAgentLogResponse,
    DashboardLearningInsightResponse,
    DashboardMetric,
    DashboardOverviewResponse,
    DashboardQueueResponse,
    DashboardTrendPoint,
    DashboardUploadResponse,
    DashboardVideoResponse,
)
from app.schemas.learning import LearningAnalysisResponse
from app.schemas.seo import SEOGenerationResponse
from app.schemas.scripts import ScriptGenerationResponse
from app.schemas.trends import TrendTopicResponse
from app.schemas.video import VideoEditingResponse
from app.schemas.visuals import VisualGenerationResponse
from app.schemas.voice import VoiceGenerationResponse
from app.schemas.youtube_upload import YouTubeUploadResponse

__all__ = [
    "AnalyticsCollectionResponse",
    "AnalyticsMetricResponse",
    "AnalyticsReportResponse",
    "DailyShortsScheduleResponse",
    "DashboardAgentLogResponse",
    "DashboardLearningInsightResponse",
    "DashboardMetric",
    "DashboardOverviewResponse",
    "DashboardQueueResponse",
    "DashboardTrendPoint",
    "DashboardUploadResponse",
    "DashboardVideoResponse",
    "EnqueuedTaskResponse",
    "LearningAnalysisResponse",
    "PurgeQueueResponse",
    "QueueInspectionResponse",
    "RevokeTaskResponse",
    "SEOGenerationResponse",
    "ScriptGenerationResponse",
    "TaskStatusResponse",
    "TrendTopicResponse",
    "VideoEditingResponse",
    "VisualGenerationResponse",
    "VoiceGenerationResponse",
    "YouTubeUploadResponse",
]
