from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.agents.trend_research import TrendResearchAgent
from app.services.trends.collectors import (
    GoogleTrendsCollector,
    NewsHeadlinesCollector,
    RedditDiscussionsCollector,
    YouTubeTrendsCollector,
)
from app.services.trends.models import TrendSignal
from app.services.trends.scoring import TrendScorer

pytestmark = pytest.mark.no_db


class FakeCollector:
    def __init__(self, source: str, signals: list[TrendSignal]) -> None:
        self.source = source
        self.signals = signals

    async def collect(
        self,
        *,
        category: str | None = None,
        limit: int = 25,
    ) -> list[TrendSignal]:
        if category is None:
            return self.signals[:limit]
        return [
            signal
            for signal in self.signals
            if signal.category == category or category in signal.title.lower()
        ][:limit]


class FailingCollector:
    source = "reddit"

    async def collect(
        self,
        *,
        category: str | None = None,
        limit: int = 25,
    ) -> list[TrendSignal]:
        raise RuntimeError("source unavailable")


@pytest.mark.asyncio
async def test_agent_outputs_scored_deduped_category_filtered_contract() -> None:
    now = datetime.now(UTC)
    collectors = [
        FakeCollector(
            "youtube",
            [
                TrendSignal(
                    source="youtube",
                    title="AI video generators are taking over Shorts",
                    category="technology",
                    keywords=["ai", "video", "shorts"],
                    engagement=250_000,
                    published_at=now - timedelta(hours=2),
                ),
                TrendSignal(
                    source="youtube",
                    title="Celebrity wedding surprise",
                    category="entertainment",
                    keywords=["celebrity"],
                    engagement=500_000,
                    published_at=now,
                ),
            ],
        ),
        FakeCollector(
            "reddit",
            [
                TrendSignal(
                    source="reddit",
                    title="AI video generator taking over short-form content",
                    category="technology",
                    keywords=["ai", "generator"],
                    engagement=8_000,
                    published_at=now - timedelta(hours=4),
                )
            ],
        ),
        FakeCollector(
            "news",
            [
                TrendSignal(
                    source="news",
                    title="New AI video tools reshape creator workflows",
                    category="technology",
                    keywords=["ai", "creator"],
                    engagement=1,
                    published_at=now - timedelta(hours=1),
                )
            ],
        ),
    ]
    agent = TrendResearchAgent(collectors=collectors, max_results=10)

    results = await agent.fetch_trending_topics(category="technology", limit=5)

    assert len(results) == 2
    assert set(results[0]) == {"topic", "score", "category", "keywords"}
    assert results[0]["topic"] == "AI video generators are taking over Shorts"
    assert results[0]["category"] == "technology"
    assert results[0]["score"] > 60
    assert {"ai", "video"}.issubset(set(results[0]["keywords"]))
    assert all(result["category"] == "technology" for result in results)


@pytest.mark.asyncio
async def test_agent_isolates_failing_collectors() -> None:
    agent = TrendResearchAgent(
        collectors=[
            FailingCollector(),
            FakeCollector(
                "news",
                [
                    TrendSignal(
                        source="news",
                        title="Robotics startup launches pocket camera drone",
                        category="technology",
                        keywords=["robotics", "drone"],
                        engagement=1,
                    )
                ],
            ),
        ]
    )

    results = await agent.fetch_trending_topics(category="technology")

    assert len(results) == 1
    assert results[0]["topic"] == "Robotics startup launches pocket camera drone"


@pytest.mark.asyncio
async def test_source_collectors_parse_provider_payloads() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "googleapis.com" in request.url.host:
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "abc123",
                            "snippet": {
                                "title": "Quantum AI Shorts explained",
                                "categoryId": "28",
                                "tags": ["Quantum", "AI"],
                                "publishedAt": "2026-06-29T12:00:00Z",
                            },
                            "statistics": {
                                "viewCount": "1000",
                                "likeCount": "50",
                                "commentCount": "10",
                            },
                        }
                    ]
                },
            )
        if "trends.google.com" in request.url.host:
            return httpx.Response(
                200,
                text=(
                    '<rss xmlns:ht="https://trends.google.com/trends/'
                    'trendingsearches/daily"><channel><item>'
                    "<title>AI agents</title>"
                    "<ht:approx_traffic>100K+</ht:approx_traffic>"
                    "<pubDate>Mon, 29 Jun 2026 12:00:00 GMT</pubDate>"
                    "</item></channel></rss>"
                ),
            )
        if "reddit.com" in request.url.host:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "children": [
                            {
                                "data": {
                                    "title": "AI editing workflow discussion",
                                    "score": 120,
                                    "num_comments": 30,
                                    "created_utc": 1_782_732_000,
                                    "permalink": "/r/youtube/comments/abc/test/",
                                    "stickied": False,
                                }
                            }
                        ]
                    }
                },
            )
        if "news.google.com" in request.url.host:
            assert "q=technology" in url
            return httpx.Response(
                200,
                text=(
                    "<rss><channel><item>"
                    "<title>Technology headline for creators</title>"
                    "<link>https://news.example/item</link>"
                    "<pubDate>Mon, 29 Jun 2026 12:00:00 GMT</pubDate>"
                    "</item></channel></rss>"
                ),
            )
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        youtube = YouTubeTrendsCollector(api_key="key", client=client)
        google = GoogleTrendsCollector(client=client)
        reddit = RedditDiscussionsCollector(
            subreddits=["youtube"],
            user_agent="test-agent",
            client=client,
        )
        news = NewsHeadlinesCollector(client=client)

        youtube_signals = await youtube.collect(category="technology")
        google_signals = await google.collect()
        reddit_signals = await reddit.collect(category="technology")
        news_signals = await news.collect(category="technology")

    assert youtube_signals[0].title == "Quantum AI Shorts explained"
    assert youtube_signals[0].category == "technology"
    assert youtube_signals[0].engagement == 1280
    assert google_signals[0].title == "AI agents"
    assert google_signals[0].engagement == 100_000
    assert (
        reddit_signals[0].url == "https://www.reddit.com/r/youtube/comments/abc/test/"
    )
    assert news_signals[0].title == "Technology headline for creators"


def test_viral_potential_increases_with_cross_source_agreement() -> None:
    scorer = TrendScorer()
    one_source = [
        TrendSignal(
            source="youtube",
            title="AI cameras for creators",
            category="technology",
            engagement=10_000,
        )
    ]
    three_sources = [
        *one_source,
        TrendSignal(
            source="reddit",
            title="AI cameras for creators",
            category="technology",
            engagement=500,
        ),
        TrendSignal(
            source="news",
            title="AI cameras for creators",
            category="technology",
            engagement=1,
        ),
    ]

    assert scorer.calculate_viral_potential(
        three_sources
    ) > scorer.calculate_viral_potential(one_source)
