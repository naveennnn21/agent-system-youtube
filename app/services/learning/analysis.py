"""Deterministic recommendation engine for future Shorts content."""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import UTC
from typing import Any

from app.services.learning.models import (
    ContentPerformanceSample,
    ContentRecommendations,
    LearningAnalysisRequest,
    LearningAnalysisResult,
    ScoredContentSample,
    WinningSignal,
)


class LearningAnalyzer:
    """Analyze historical performance and produce future content guidance."""

    def analyze(
        self,
        samples: list[ContentPerformanceSample],
        request: LearningAnalysisRequest | None = None,
    ) -> LearningAnalysisResult:
        request = request or LearningAnalysisRequest()
        eligible = [
            sample for sample in samples
            if sample.metrics.get("views", 0) >= request.min_views
        ]
        if not eligible:
            return _empty_result(request)

        max_views = max(sample.metrics.get("views", 0) for sample in eligible) or 1
        scored = [
            ScoredContentSample(
                sample=sample,
                score=_performance_score(sample, max_views=max_views),
            )
            for sample in eligible
        ]
        scored.sort(key=lambda item: item.score, reverse=True)
        winners = scored[: max(1, request.top_n)]
        baseline_score = round(statistics.fmean(item.score for item in scored), 2)

        winning_hooks = _winning_hooks(winners)
        winning_topics = _winning_topics(winners)
        winning_posting_times = _winning_posting_times(winners)
        best_formats = _best_formats(winners)
        recommendations = _build_recommendations(
            winning_hooks=winning_hooks,
            winning_topics=winning_topics,
            winning_posting_times=winning_posting_times,
            best_formats=best_formats,
            winners=winners,
            sample_count=len(eligible),
        )

        return LearningAnalysisResult(
            sample_count=len(eligible),
            winner_count=len(winners),
            baseline_score=baseline_score,
            top_videos=winners,
            winning_hooks=winning_hooks,
            winning_topics=winning_topics,
            winning_posting_times=winning_posting_times,
            best_formats=best_formats,
            recommendations=recommendations,
            model_version=request.model_version,
        )


def classify_format(
    *,
    duration_seconds: int | None,
    aspect_ratio: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Return a stable format bucket for a rendered Short."""
    metadata = metadata or {}
    explicit = metadata.get("format") or metadata.get("video_format")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip().lower().replace(" ", "_")[:64]

    duration = duration_seconds or 0
    if duration <= 35:
        pace = "fast_cut"
    elif duration <= 50:
        pace = "standard_short"
    else:
        pace = "story_short"
    ratio = "vertical" if aspect_ratio == "9:16" else aspect_ratio.replace(":", "x")
    return f"{pace}_{ratio}"


def hook_pattern(hook: str) -> str:
    """Classify a hook into a reusable creative pattern."""
    text = hook.lower()
    if any(char.isdigit() for char in hook):
        return "numbered_payoff"
    if "?" in hook or text.startswith(("what", "why", "how")):
        return "curiosity_question"
    if any(term in text for term in ("mistake", "wrong", "stop", "avoid")):
        return "mistake_warning"
    if any(term in text for term in ("secret", "nobody", "hidden", "most people")):
        return "hidden_truth"
    if any(term in text for term in ("before", "after", "instead", "but")):
        return "contrast_loop"
    return "direct_benefit"


def _performance_score(sample: ContentPerformanceSample, *, max_views: float) -> float:
    views = sample.metrics.get("views", 0)
    likes = sample.metrics.get("likes", 0)
    comments = sample.metrics.get("comments", 0)
    shares = sample.metrics.get("shares", 0)
    subscribers = sample.metrics.get("subscribers_gained", 0)
    retention = sample.metrics.get("retention_rate", 0)
    ctr = sample.metrics.get("click_through_rate", 0)
    avg_view_duration = sample.metrics.get("average_view_duration_seconds", 0)

    view_score = _safe_ratio(math.log1p(views), math.log1p(max_views)) * 35
    engagement_rate = _safe_ratio(likes + comments * 2 + shares * 3, views)
    engagement_score = min(engagement_rate * 500, 20)
    retention_score = min(max(retention, 0), 1) * 20
    ctr_score = min(max(ctr, 0), 1) * 10
    subscriber_score = min(_safe_ratio(subscribers, max(views, 1)) * 2000, 10)

    duration_score = 0.0
    if sample.duration_seconds and avg_view_duration:
        duration_score = min(_safe_ratio(avg_view_duration, sample.duration_seconds), 1) * 5

    return round(
        view_score
        + engagement_score
        + retention_score
        + ctr_score
        + subscriber_score
        + duration_score,
        2,
    )


def _winning_hooks(winners: list[ScoredContentSample]) -> list[WinningSignal]:
    grouped: dict[str, list[ScoredContentSample]] = defaultdict(list)
    for winner in winners:
        if winner.sample.hook:
            grouped[hook_pattern(winner.sample.hook)].append(winner)

    signals: list[WinningSignal] = []
    for pattern, items in grouped.items():
        best = max(items, key=lambda item: item.score)
        signals.append(
            WinningSignal(
                signal="winning_hook",
                value=pattern,
                score=_avg_score(items),
                count=len(items),
                evidence=[_evidence(item) | {"hook": item.sample.hook} for item in items[:3]],
                recommendation=_hook_recommendation(pattern, best.sample.topic),
            )
        )
    return sorted(signals, key=lambda signal: signal.score, reverse=True)


def _winning_topics(winners: list[ScoredContentSample]) -> list[WinningSignal]:
    grouped: dict[str, list[ScoredContentSample]] = defaultdict(list)
    for winner in winners:
        topic = winner.sample.topic or winner.sample.title
        if topic:
            grouped[topic].append(winner)

    return sorted(
        [
            WinningSignal(
                signal="winning_topic",
                value=topic,
                score=_avg_score(items),
                count=len(items),
                evidence=[_evidence(item) | {"keywords": item.sample.keywords} for item in items[:3]],
                recommendation=f"Generate adjacent angles around '{topic}' using proven keywords.",
            )
            for topic, items in grouped.items()
        ],
        key=lambda signal: signal.score,
        reverse=True,
    )


def _winning_posting_times(winners: list[ScoredContentSample]) -> list[WinningSignal]:
    grouped: dict[str, list[ScoredContentSample]] = defaultdict(list)
    for winner in winners:
        timestamp = winner.sample.published_at or winner.sample.scheduled_at
        if timestamp is None:
            continue
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        timestamp = timestamp.astimezone(UTC)
        slot = f"{timestamp.strftime('%A')} {timestamp.hour:02d}:00 UTC"
        grouped[slot].append(winner)

    return sorted(
        [
            WinningSignal(
                signal="winning_posting_time",
                value=slot,
                score=_avg_score(items),
                count=len(items),
                evidence=[_evidence(item) for item in items[:3]],
                recommendation=f"Schedule future Shorts near {slot} when audience response is strongest.",
            )
            for slot, items in grouped.items()
        ],
        key=lambda signal: signal.score,
        reverse=True,
    )


def _best_formats(winners: list[ScoredContentSample]) -> list[WinningSignal]:
    grouped: dict[str, list[ScoredContentSample]] = defaultdict(list)
    for winner in winners:
        grouped[winner.sample.format_label].append(winner)

    return sorted(
        [
            WinningSignal(
                signal="best_format",
                value=format_label,
                score=_avg_score(items),
                count=len(items),
                evidence=[
                    _evidence(item)
                    | {
                        "duration_seconds": item.sample.duration_seconds,
                        "aspect_ratio": item.sample.aspect_ratio,
                    }
                    for item in items[:3]
                ],
                recommendation=f"Use the '{format_label}' structure for similar topics.",
            )
            for format_label, items in grouped.items()
        ],
        key=lambda signal: signal.score,
        reverse=True,
    )


def _build_recommendations(
    *,
    winning_hooks: list[WinningSignal],
    winning_topics: list[WinningSignal],
    winning_posting_times: list[WinningSignal],
    best_formats: list[WinningSignal],
    winners: list[ScoredContentSample],
    sample_count: int,
) -> ContentRecommendations:
    next_topics = [
        {
            "topic": signal.value,
            "score": signal.score,
            "keywords": _top_keywords(signal.evidence),
            "reason": signal.recommendation,
        }
        for signal in winning_topics[:5]
    ]
    hook_templates = [
        {
            "pattern": signal.value,
            "template": _hook_template(signal.value),
            "score": signal.score,
            "reason": signal.recommendation,
        }
        for signal in winning_hooks[:5]
    ]
    posting_schedule = [
        {
            "slot": signal.value,
            "score": signal.score,
            "reason": signal.recommendation,
        }
        for signal in winning_posting_times[:5]
    ]
    duration_values = [
        item.sample.duration_seconds
        for item in winners
        if item.sample.duration_seconds is not None
    ]
    best_format = best_formats[0].value if best_formats else "standard_short_vertical"
    format_defaults = {
        "format": best_format,
        "duration_seconds": round(statistics.fmean(duration_values)) if duration_values else 45,
        "aspect_ratio": "9:16",
        "pacing": best_format.split("_")[0],
    }
    top_keywords = _top_keywords([signal.to_dict() for signal in winning_topics])
    generation_hints = {
        "preferred_hook_patterns": [signal.value for signal in winning_hooks[:3]],
        "preferred_topics": [signal.value for signal in winning_topics[:5]],
        "preferred_keywords": top_keywords,
        "preferred_posting_slots": [signal.value for signal in winning_posting_times[:3]],
        "preferred_format": format_defaults,
        "avoid": ["untested hooks with no clear payoff", "posting outside proven slots"],
    }
    confidence = min(100.0, round((len(winners) / max(sample_count, 1)) * 50 + len(winners) * 8, 1))
    return ContentRecommendations(
        next_topics=next_topics,
        hook_templates=hook_templates,
        posting_schedule=posting_schedule,
        format_defaults=format_defaults,
        generation_hints=generation_hints,
        confidence=confidence,
    )


def _empty_result(request: LearningAnalysisRequest) -> LearningAnalysisResult:
    recommendations = ContentRecommendations(
        next_topics=[],
        hook_templates=[],
        posting_schedule=[],
        format_defaults={"format": "standard_short_vertical", "duration_seconds": 45, "aspect_ratio": "9:16"},
        generation_hints={
            "preferred_hook_patterns": [],
            "preferred_topics": [],
            "preferred_keywords": [],
            "preferred_posting_slots": [],
            "preferred_format": {"format": "standard_short_vertical", "duration_seconds": 45, "aspect_ratio": "9:16"},
            "avoid": [],
        },
        confidence=0.0,
    )
    return LearningAnalysisResult(
        sample_count=0,
        winner_count=0,
        baseline_score=0.0,
        top_videos=[],
        winning_hooks=[],
        winning_topics=[],
        winning_posting_times=[],
        best_formats=[],
        recommendations=recommendations,
        model_version=request.model_version,
    )


def _avg_score(items: list[ScoredContentSample]) -> float:
    return round(statistics.fmean(item.score for item in items), 2)


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _evidence(item: ScoredContentSample) -> dict[str, Any]:
    return {
        "video_id": str(item.sample.video_id) if item.sample.video_id else None,
        "topic_id": str(item.sample.topic_id) if item.sample.topic_id else None,
        "script_id": str(item.sample.script_id) if item.sample.script_id else None,
        "analytics_id": str(item.sample.analytics_id) if item.sample.analytics_id else None,
        "title": item.sample.title,
        "topic": item.sample.topic,
        "score": item.score,
        "views": item.sample.metrics.get("views", 0),
        "retention_rate": item.sample.metrics.get("retention_rate", 0),
        "click_through_rate": item.sample.metrics.get("click_through_rate", 0),
    }


def _hook_recommendation(pattern: str, topic: str) -> str:
    template = _hook_template(pattern)
    return f"Use {pattern.replace('_', ' ')} hooks for {topic or 'future topics'}: {template}"


def _hook_template(pattern: str) -> str:
    templates = {
        "numbered_payoff": "Give a truthful number plus a concrete payoff: '3 ways [topic] saves you hours.'",
        "curiosity_question": "Open with a specific question that the final seconds answer.",
        "mistake_warning": "Name the common mistake first, then show the simpler fix.",
        "hidden_truth": "Reveal a counterintuitive truth without overstating the claim.",
        "contrast_loop": "Show before versus after, then close the loop near the end.",
        "direct_benefit": "Lead with the exact viewer benefit in plain spoken language.",
    }
    return templates.get(pattern, templates["direct_benefit"])


def _top_keywords(evidence_items: list[dict[str, Any]]) -> list[str]:
    counts: dict[str, int] = defaultdict(int)
    for evidence in evidence_items:
        for keyword in evidence.get("keywords", []) or []:
            if isinstance(keyword, str) and keyword.strip():
                counts[keyword.strip()] += 1
        for nested in evidence.get("evidence", []) or []:
            for keyword in nested.get("keywords", []) or []:
                if isinstance(keyword, str) and keyword.strip():
                    counts[keyword.strip()] += 1
    return [
        keyword
        for keyword, _ in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0].lower()),
        )[:10]
    ]
