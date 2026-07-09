"""Trend scoring, category filtering, and deduplication."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Iterable

from app.services.trends.models import TrendSignal, TrendTopic

SOURCE_WEIGHTS = {
    "youtube": 0.34,
    "google_trends": 0.28,
    "reddit": 0.2,
    "news": 0.18,
}

STOPWORDS = {
    "about",
    "after",
    "again",
    "and",
    "are",
    "but",
    "for",
    "from",
    "has",
    "have",
    "how",
    "into",
    "new",
    "now",
    "the",
    "this",
    "that",
    "with",
    "you",
    "your",
}


@dataclass(slots=True)
class _TrendCluster:
    title: str
    category: str
    tokens: set[str]
    signals: list[TrendSignal] = field(default_factory=list)


class TrendScorer:
    """Score and rank trend signals into public topic outputs."""

    def score(
        self,
        signals: Iterable[TrendSignal],
        *,
        category: str | None = None,
        limit: int = 25,
    ) -> list[TrendTopic]:
        """Return scored, deduplicated topics."""
        filtered = [
            signal
            for signal in signals
            if signal.title and self._matches_category(signal, category)
        ]
        clusters = self._deduplicate(filtered)
        topics = [self._score_cluster(cluster) for cluster in clusters]
        topics.sort(key=lambda item: item.score, reverse=True)
        return topics[:limit]

    def calculate_viral_potential(self, signals: list[TrendSignal]) -> float:
        """Calculate viral potential from merged source signals."""
        if not signals:
            return 0.0

        unique_sources = {signal.source for signal in signals}
        source_weight = min(
            1.0,
            sum(SOURCE_WEIGHTS.get(source, 0.1) for source in unique_sources),
        )
        total_engagement = sum(max(signal.engagement, 0.0) for signal in signals)
        engagement_score = min(1.0, math.log10(total_engagement + 1) / 6)
        cross_source_score = min(1.0, len(unique_sources) / 3)
        recency_score = max(self._recency_score(signal) for signal in signals)
        keyword_score = min(1.0, len(self._merged_keywords(signals)) / 8)

        score = (
            (engagement_score * 0.35)
            + (cross_source_score * 0.25)
            + (source_weight * 0.2)
            + (recency_score * 0.1)
            + (keyword_score * 0.1)
        )
        return round(score * 100, 2)

    def _score_cluster(self, cluster: _TrendCluster) -> TrendTopic:
        return TrendTopic(
            topic=cluster.title,
            score=self.calculate_viral_potential(cluster.signals),
            category=cluster.category,
            keywords=self._merged_keywords(cluster.signals),
        )

    def _deduplicate(self, signals: list[TrendSignal]) -> list[_TrendCluster]:
        clusters: list[_TrendCluster] = []

        for signal in signals:
            tokens = _tokenize(signal.title)
            if not tokens:
                continue

            match = next(
                (
                    cluster
                    for cluster in clusters
                    if _jaccard_similarity(tokens, cluster.tokens) >= 0.5
                ),
                None,
            )

            if match is None:
                clusters.append(
                    _TrendCluster(
                        title=_clean_topic(signal.title),
                        category=self._normalize_category(signal.category),
                        tokens=tokens,
                        signals=[signal],
                    )
                )
            else:
                match.signals.append(signal)
                match.tokens.update(tokens)
                if len(signal.title) < len(match.title):
                    match.title = _clean_topic(signal.title)
                match.category = self._best_category(match.signals)

        return clusters

    def _matches_category(self, signal: TrendSignal, category: str | None) -> bool:
        if not category:
            return True
        expected = category.lower()
        actual = self._normalize_category(signal.category)
        return (
            actual == expected
            or expected in actual
            or expected in signal.title.lower()
            or expected in {keyword.lower() for keyword in signal.keywords}
        )

    def _best_category(self, signals: list[TrendSignal]) -> str:
        counts: dict[str, float] = {}
        for signal in signals:
            category = self._normalize_category(signal.category)
            counts[category] = counts.get(category, 0.0) + SOURCE_WEIGHTS.get(
                signal.source,
                0.1,
            )
        return max(counts, key=lambda category: counts[category], default="general")

    def _normalize_category(self, category: str | None) -> str:
        return (category or "general").strip().lower() or "general"

    def _merged_keywords(self, signals: list[TrendSignal]) -> list[str]:
        seen: set[str] = set()
        keywords: list[str] = []
        for signal in signals:
            candidates = [*signal.keywords, *_tokenize(signal.title)]
            for candidate in candidates:
                keyword = candidate.lower().strip()
                if keyword in STOPWORDS or len(keyword) < 2 or keyword in seen:
                    continue
                seen.add(keyword)
                keywords.append(keyword)
        return keywords[:10]

    def _recency_score(self, signal: TrendSignal) -> float:
        if signal.published_at is None:
            return 0.4

        published_at = signal.published_at
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=UTC)
        age_hours = max(0.0, (datetime.now(UTC) - published_at).total_seconds() / 3600)

        if age_hours <= 6:
            return 1.0
        if age_hours <= 24:
            return 0.85
        if age_hours <= 72:
            return 0.65
        if age_hours <= 168:
            return 0.4
        return 0.2


def _tokenize(value: str) -> set[str]:
    return {
        _normalize_token(token)
        for token in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]{1,}", value.lower())
        if token not in STOPWORDS
    }


def _jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _clean_topic(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_token(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 4 and token.endswith("s"):
        return token[:-1]
    return token
