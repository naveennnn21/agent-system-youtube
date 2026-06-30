"""Trend research service package."""

from app.services.trends.collectors import (
    GoogleTrendsCollector,
    NewsHeadlinesCollector,
    RedditDiscussionsCollector,
    YouTubeTrendsCollector,
)
from app.services.trends.models import TrendSignal, TrendTopic
from app.services.trends.scoring import TrendScorer

__all__ = [
    "GoogleTrendsCollector",
    "NewsHeadlinesCollector",
    "RedditDiscussionsCollector",
    "TrendScorer",
    "TrendSignal",
    "TrendTopic",
    "YouTubeTrendsCollector",
]
