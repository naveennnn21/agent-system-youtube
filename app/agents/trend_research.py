"""Trend Research Agent.

The agent gathers external trend signals, deduplicates overlapping stories, and
returns a compact scoring contract suitable for script generation:

``{"topic": str, "score": float, "category": str, "keywords": list[str]}``
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable

from app.core.config import Settings, get_settings
from app.services.trends.collectors import (
    BaseTrendCollector,
    GoogleTrendsCollector,
    NewsHeadlinesCollector,
    RedditDiscussionsCollector,
    YouTubeTrendsCollector,
)
from app.services.trends.models import TrendSignal, TrendTopic
from app.services.trends.scoring import TrendScorer

logger = logging.getLogger(__name__)


class TrendResearchAgent:
    """Collect and rank topics for YouTube Shorts ideation."""

    def __init__(
        self,
        *,
        collectors: Iterable[BaseTrendCollector],
        scorer: TrendScorer | None = None,
        max_results: int = 25,
    ) -> None:
        self.collectors = list(collectors)
        self.scorer = scorer or TrendScorer()
        self.max_results = max_results

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "TrendResearchAgent":
        """Create the production agent from application settings."""
        settings = settings or get_settings()
        collectors: list[BaseTrendCollector] = [
            YouTubeTrendsCollector(
                api_key=settings.YOUTUBE_API_KEY,
                region_code=settings.TREND_GEO,
                timeout=settings.TREND_HTTP_TIMEOUT,
            ),
            GoogleTrendsCollector(
                geo=settings.TREND_GEO,
                timeout=settings.TREND_HTTP_TIMEOUT,
            ),
            RedditDiscussionsCollector(
                subreddits=settings.TREND_REDDIT_SUBREDDITS,
                user_agent=settings.REDDIT_USER_AGENT,
                timeout=settings.TREND_HTTP_TIMEOUT,
            ),
            NewsHeadlinesCollector(
                geo=settings.TREND_GEO,
                timeout=settings.TREND_HTTP_TIMEOUT,
            ),
        ]
        return cls(
            collectors=collectors,
            max_results=settings.TREND_MAX_RESULTS,
        )

    async def fetch_trending_topics(
        self,
        *,
        category: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Fetch, score, and return trending topic dictionaries."""
        topics = await self.research(category=category, limit=limit)
        return [topic.to_dict() for topic in topics]

    async def research(
        self,
        *,
        category: str | None = None,
        limit: int | None = None,
    ) -> list[TrendTopic]:
        """Run all collectors and score the combined result set."""
        max_results = limit or self.max_results
        signals = await self.collect_signals(category=category, limit=max_results)
        return self.scorer.score(signals, category=category, limit=max_results)

    async def collect_signals(
        self,
        *,
        category: str | None = None,
        limit: int | None = None,
    ) -> list[TrendSignal]:
        """Collect raw signals from all configured sources."""
        max_results = limit or self.max_results
        results = await asyncio.gather(
            *[
                self._safe_collect(
                    collector,
                    category=category,
                    limit=max_results,
                )
                for collector in self.collectors
            ],
            return_exceptions=False,
        )
        return [signal for group in results for signal in group]

    async def collect_youtube_trends(
        self,
        *,
        category: str | None = None,
        limit: int | None = None,
    ) -> list[TrendSignal]:
        """Collect YouTube trends from configured YouTube collectors."""
        return await self._collect_by_source("youtube", category=category, limit=limit)

    async def collect_google_trends(
        self,
        *,
        category: str | None = None,
        limit: int | None = None,
    ) -> list[TrendSignal]:
        """Collect Google Trends signals."""
        return await self._collect_by_source(
            "google_trends",
            category=category,
            limit=limit,
        )

    async def collect_reddit_discussions(
        self,
        *,
        category: str | None = None,
        limit: int | None = None,
    ) -> list[TrendSignal]:
        """Collect Reddit discussion signals."""
        return await self._collect_by_source("reddit", category=category, limit=limit)

    async def collect_news_headlines(
        self,
        *,
        category: str | None = None,
        limit: int | None = None,
    ) -> list[TrendSignal]:
        """Collect news headline signals."""
        return await self._collect_by_source("news", category=category, limit=limit)

    async def _collect_by_source(
        self,
        source: str,
        *,
        category: str | None,
        limit: int | None,
    ) -> list[TrendSignal]:
        max_results = limit or self.max_results
        matching = [
            collector
            for collector in self.collectors
            if getattr(collector, "source", None) == source
        ]
        results = await asyncio.gather(
            *[
                self._safe_collect(
                    collector,
                    category=category,
                    limit=max_results,
                )
                for collector in matching
            ],
            return_exceptions=False,
        )
        return [signal for group in results for signal in group]

    async def _safe_collect(
        self,
        collector: BaseTrendCollector,
        *,
        category: str | None,
        limit: int,
    ) -> list[TrendSignal]:
        try:
            return await collector.collect(category=category, limit=limit)
        except Exception:
            logger.exception("Trend collector failed: %s", collector.source)
            return []
