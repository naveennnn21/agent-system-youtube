"""External trend collectors.

Collectors are intentionally thin and return normalized ``TrendSignal`` rows.
The scoring layer handles deduplication, category filtering, and ranking.
"""

from __future__ import annotations

import logging
import math
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote_plus

import httpx

from app.services.trends.models import TrendSignal

logger = logging.getLogger(__name__)

YOUTUBE_MOST_POPULAR_URL = "https://www.googleapis.com/youtube/v3/videos"
GOOGLE_TRENDS_RSS_URL = (
    "https://trends.google.com/trends/trendingsearches/daily/rss"
)
GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss"
REDDIT_HOT_URL = "https://www.reddit.com/r/{subreddit}/hot.json"

YOUTUBE_CATEGORY_MAP = {
    "1": "film",
    "2": "autos",
    "10": "music",
    "15": "pets",
    "17": "sports",
    "19": "travel",
    "20": "gaming",
    "22": "people",
    "23": "comedy",
    "24": "entertainment",
    "25": "news",
    "26": "lifestyle",
    "27": "education",
    "28": "technology",
}


class BaseTrendCollector:
    """Interface for a source-specific trend collector."""

    source: str = "unknown"

    async def collect(
        self,
        *,
        category: str | None = None,
        limit: int = 25,
    ) -> list[TrendSignal]:
        raise NotImplementedError


class HttpTrendCollector(BaseTrendCollector):
    """Base collector with optional injected ``httpx.AsyncClient``."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._client = client
        self._timeout = timeout

    async def _get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if self._client is not None:
            response = await self._client.get(url, params=params, headers=headers)
        else:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params, headers=headers)

        response.raise_for_status()
        return response.json()

    async def _get_text(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        if self._client is not None:
            response = await self._client.get(url, params=params, headers=headers)
        else:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params, headers=headers)

        response.raise_for_status()
        return response.text


class YouTubeTrendsCollector(HttpTrendCollector):
    """Collect most-popular videos from the YouTube Data API."""

    source = "youtube"

    def __init__(
        self,
        *,
        api_key: str = "",
        region_code: str = "US",
        client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
    ) -> None:
        super().__init__(client=client, timeout=timeout)
        self.api_key = api_key
        self.region_code = region_code

    async def collect(
        self,
        *,
        category: str | None = None,
        limit: int = 25,
    ) -> list[TrendSignal]:
        if not self.api_key:
            logger.info("Skipping YouTube trend collection: YOUTUBE_API_KEY is empty.")
            return []

        params = {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": self.region_code,
            "maxResults": min(limit, 50),
            "key": self.api_key,
        }

        try:
            payload = await self._get_json(YOUTUBE_MOST_POPULAR_URL, params=params)
        except httpx.HTTPError as exc:
            logger.warning("YouTube trend collection failed: %s", exc)
            return []

        signals: list[TrendSignal] = []
        for item in payload.get("items", []):
            snippet = item.get("snippet", {})
            statistics = item.get("statistics", {})
            title = str(snippet.get("title") or "").strip()
            if not title:
                continue

            video_category = YOUTUBE_CATEGORY_MAP.get(
                str(snippet.get("categoryId") or ""),
                "general",
            )
            if category and not _category_matches(video_category, category, title):
                continue

            views = _safe_float(statistics.get("viewCount"))
            likes = _safe_float(statistics.get("likeCount"))
            comments = _safe_float(statistics.get("commentCount"))
            engagement = views + (likes * 4) + (comments * 8)
            video_id = item.get("id")

            signals.append(
                TrendSignal(
                    source=self.source,
                    title=title,
                    category=video_category,
                    keywords=_clean_keywords(snippet.get("tags", [])),
                    engagement=engagement,
                    url=f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
                    published_at=_parse_datetime(snippet.get("publishedAt")),
                    metadata={"video_id": video_id, "statistics": statistics},
                )
            )

        return signals


class GoogleTrendsCollector(HttpTrendCollector):
    """Collect daily Google Trends searches from the public RSS feed."""

    source = "google_trends"

    def __init__(
        self,
        *,
        geo: str = "US",
        client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
    ) -> None:
        super().__init__(client=client, timeout=timeout)
        self.geo = geo

    async def collect(
        self,
        *,
        category: str | None = None,
        limit: int = 25,
    ) -> list[TrendSignal]:
        params = {"geo": self.geo}
        try:
            xml_text = await self._get_text(GOOGLE_TRENDS_RSS_URL, params=params)
        except httpx.HTTPError as exc:
            logger.warning("Google Trends collection failed: %s", exc)
            return []

        signals = _parse_rss_items(
            xml_text,
            source=self.source,
            default_category=category or "general",
            limit=limit,
            engagement_getter=_google_trends_engagement,
        )
        return _filter_signals_by_category(signals, category)


class RedditDiscussionsCollector(HttpTrendCollector):
    """Collect hot discussions from configured subreddits."""

    source = "reddit"

    def __init__(
        self,
        *,
        subreddits: list[str] | tuple[str, ...],
        user_agent: str,
        client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
    ) -> None:
        super().__init__(client=client, timeout=timeout)
        self.subreddits = list(subreddits)
        self.user_agent = user_agent

    async def collect(
        self,
        *,
        category: str | None = None,
        limit: int = 25,
    ) -> list[TrendSignal]:
        signals: list[TrendSignal] = []
        per_subreddit = max(1, math.ceil(limit / max(len(self.subreddits), 1)))

        for subreddit in self.subreddits:
            url = REDDIT_HOT_URL.format(subreddit=subreddit)
            params = {"limit": per_subreddit}
            headers = {"User-Agent": self.user_agent}
            try:
                payload = await self._get_json(url, params=params, headers=headers)
            except httpx.HTTPError as exc:
                logger.warning("Reddit collection failed for r/%s: %s", subreddit, exc)
                continue

            children = payload.get("data", {}).get("children", [])
            for child in children:
                data = child.get("data", {})
                title = str(data.get("title") or "").strip()
                if not title or data.get("stickied"):
                    continue

                inferred_category = _infer_category(title, fallback=subreddit.lower())
                if category and not _category_matches(inferred_category, category, title):
                    continue

                score = _safe_float(data.get("score"))
                comments = _safe_float(data.get("num_comments"))
                signals.append(
                    TrendSignal(
                        source=self.source,
                        title=title,
                        category=inferred_category,
                        keywords=_extract_title_keywords(title),
                        engagement=score + (comments * 3),
                        url=_reddit_url(data.get("permalink")),
                        published_at=_parse_unix_timestamp(data.get("created_utc")),
                        metadata={
                            "subreddit": subreddit,
                            "score": score,
                            "comments": comments,
                        },
                    )
                )

        return signals[:limit]


class NewsHeadlinesCollector(HttpTrendCollector):
    """Collect current headlines from Google News RSS."""

    source = "news"

    def __init__(
        self,
        *,
        geo: str = "US",
        client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
    ) -> None:
        super().__init__(client=client, timeout=timeout)
        self.geo = geo

    async def collect(
        self,
        *,
        category: str | None = None,
        limit: int = 25,
    ) -> list[TrendSignal]:
        if category:
            url = f"{GOOGLE_NEWS_RSS_URL}/search?q={quote_plus(category)}&hl=en-US&gl={self.geo}&ceid={self.geo}:en"
            default_category = category
        else:
            url = f"{GOOGLE_NEWS_RSS_URL}?hl=en-US&gl={self.geo}&ceid={self.geo}:en"
            default_category = "news"

        try:
            xml_text = await self._get_text(url)
        except httpx.HTTPError as exc:
            logger.warning("News headline collection failed: %s", exc)
            return []

        signals = _parse_rss_items(
            xml_text,
            source=self.source,
            default_category=default_category,
            limit=limit,
            engagement_getter=lambda _item: 1.0,
        )
        return _filter_signals_by_category(signals, category)


def _parse_rss_items(
    xml_text: str,
    *,
    source: str,
    default_category: str,
    limit: int,
    engagement_getter,
) -> list[TrendSignal]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("Unable to parse %s RSS payload: %s", source, exc)
        return []

    signals: list[TrendSignal] = []
    for item in root.findall(".//item"):
        title = _child_text(item, "title")
        if not title:
            continue

        category = _child_text(item, "category") or _infer_category(
            title,
            fallback=default_category,
        )
        signals.append(
            TrendSignal(
                source=source,
                title=title,
                category=category.lower(),
                keywords=_extract_title_keywords(title),
                engagement=engagement_getter(item),
                url=_child_text(item, "link"),
                published_at=_parse_datetime(_child_text(item, "pubDate")),
                metadata={"description": _child_text(item, "description")},
            )
        )
        if len(signals) >= limit:
            break

    return signals


def _google_trends_engagement(item: ET.Element) -> float:
    traffic_text = _child_text(item, "approx_traffic")
    if not traffic_text:
        return 1.0
    multiplier = 1.0
    normalized = traffic_text.replace("+", "").replace(",", "").strip().lower()
    if normalized.endswith("k"):
        multiplier = 1_000
        normalized = normalized[:-1]
    elif normalized.endswith("m"):
        multiplier = 1_000_000
        normalized = normalized[:-1]
    return _safe_float(normalized) * multiplier


def _child_text(item: ET.Element, local_name: str) -> str | None:
    for child in item:
        if child.tag.rsplit("}", 1)[-1] == local_name and child.text:
            return child.text.strip()
    return None


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    try:
        if text.endswith("Z"):
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    except (TypeError, ValueError):
        return None


def _parse_unix_timestamp(value: Any) -> datetime | None:
    try:
        return datetime.fromtimestamp(float(value), tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _reddit_url(permalink: Any) -> str | None:
    if not permalink:
        return None
    text = str(permalink)
    if text.startswith("http"):
        return text
    return f"https://www.reddit.com{text}"


def _clean_keywords(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip().lower() for value in values if str(value).strip()]


def _extract_title_keywords(title: str) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]{2,}", title.lower())
    stopwords = {
        "and",
        "are",
        "for",
        "from",
        "has",
        "how",
        "new",
        "the",
        "this",
        "that",
        "with",
        "you",
        "your",
    }
    seen: set[str] = set()
    keywords: list[str] = []
    for word in words:
        if word in stopwords or word in seen:
            continue
        seen.add(word)
        keywords.append(word)
    return keywords[:8]


def _filter_signals_by_category(
    signals: list[TrendSignal],
    category: str | None,
) -> list[TrendSignal]:
    if not category:
        return signals
    return [
        signal
        for signal in signals
        if _category_matches(signal.category, category, signal.title)
    ]


def _category_matches(actual: str, expected: str, title: str) -> bool:
    actual_norm = actual.lower()
    expected_norm = expected.lower()
    return (
        actual_norm == expected_norm
        or expected_norm in actual_norm
        or expected_norm in title.lower()
    )


def _infer_category(title: str, *, fallback: str = "general") -> str:
    text = title.lower()
    category_terms = {
        "technology": {"ai", "app", "software", "startup", "tech", "robot"},
        "business": {"business", "market", "startup", "stock", "company"},
        "entertainment": {"movie", "music", "celebrity", "show", "trailer"},
        "sports": {"game", "match", "nfl", "nba", "soccer", "cricket"},
        "health": {"health", "fitness", "doctor", "sleep", "diet"},
        "education": {"learn", "study", "school", "science", "explained"},
        "news": {"election", "policy", "court", "breaking", "government"},
    }
    for category, terms in category_terms.items():
        if any(term in text for term in terms):
            return category
    return fallback.lower() or "general"
