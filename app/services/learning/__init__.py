"""Learning and recommendation service package."""

from app.services.learning.analysis import (
    LearningAnalyzer,
    classify_format,
    hook_pattern,
)
from app.services.learning.models import (
    ContentPerformanceSample,
    ContentRecommendations,
    LearningAnalysisRequest,
    LearningAnalysisResult,
    ScoredContentSample,
    WinningSignal,
)

__all__ = [
    "ContentPerformanceSample",
    "ContentRecommendations",
    "LearningAnalysisRequest",
    "LearningAnalysisResult",
    "LearningAnalyzer",
    "ScoredContentSample",
    "WinningSignal",
    "classify_format",
    "hook_pattern",
]
