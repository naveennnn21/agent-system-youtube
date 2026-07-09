"""CTR and discoverability evaluation for YouTube metadata."""

from __future__ import annotations

import re

from app.services.seo.models import SEOEvaluation, SEOMetadata

CTR_TERMS = {
    "how",
    "why",
    "secret",
    "mistake",
    "truth",
    "before",
    "after",
    "actually",
    "surprising",
}
ACTION_TERMS = {
    "watch",
    "try",
    "learn",
    "discover",
    "save",
    "share",
    "comment",
    "subscribe",
}


class SEOEvaluator:
    """Score metadata with deterministic, provider-independent checks."""

    def __init__(self, *, minimum_score: float = 60.0) -> None:
        self.minimum_score = minimum_score

    def evaluate(
        self,
        metadata: SEOMetadata,
        *,
        topic: str,
        seed_keywords: list[str] | None = None,
    ) -> SEOEvaluation:
        candidates = _candidate_phrases(topic, seed_keywords or [])
        ctr_score = self._ctr_score(metadata.title, candidates)
        discoverability_score = self._discoverability_score(metadata, candidates)
        description_score = self._description_score(metadata.description, candidates)
        overall_score = round(
            ctr_score * 0.45 + discoverability_score * 0.4 + description_score * 0.15,
            1,
        )

        issues: list[str] = []
        suggestions: list[str] = []
        if len(metadata.title) > 100:
            issues.append("Title exceeds YouTube's 100-character limit.")
        if not metadata.hashtags:
            issues.append("At least one hashtag is required.")
        if not metadata.keywords:
            issues.append("At least one keyword is required.")
        if not any(_contains_phrase(metadata.title, phrase) for phrase in candidates):
            issues.append("Title does not contain the topic or a seed keyword.")
            suggestions.append(
                "Place the primary search phrase naturally in the title."
            )
        if ctr_score < 60:
            issues.append("Title needs a stronger qualified-click signal.")
            suggestions.append(
                "Use a specific benefit, contrast, question, or truthful number."
            )
        if discoverability_score < 60:
            issues.append("Metadata has weak search coverage.")
            suggestions.append("Add relevant broad and long-tail keyword variants.")
        if description_score < 55:
            issues.append("Description needs a clearer summary or viewer action.")
            suggestions.append("Open with the payoff and end with one concise action.")
        if overall_score < self.minimum_score:
            issues.append(f"Overall SEO score is below {self.minimum_score:g}.")

        return SEOEvaluation(
            ctr_score=ctr_score,
            discoverability_score=discoverability_score,
            description_score=description_score,
            overall_score=overall_score,
            is_valid=not issues,
            issues=issues,
            suggestions=suggestions,
        )

    def _ctr_score(self, title: str, candidates: list[str]) -> float:
        normalized = title.lower()
        score = 25.0
        if 35 <= len(title) <= 70:
            score += 20
        elif len(title) <= 100:
            score += 10
        if any(_contains_phrase(title, phrase) for phrase in candidates):
            score += 25
        if any(term in _words(normalized) for term in CTR_TERMS):
            score += 15
        if any(char.isdigit() for char in title):
            score += 10
        if "?" in title:
            score += 8
        if title.count("!") > 1 or title.count("?") > 1:
            score -= 15
        if title.isupper() and any(char.isalpha() for char in title):
            score -= 20
        return round(max(0.0, min(score, 100.0)), 1)

    def _discoverability_score(
        self,
        metadata: SEOMetadata,
        candidates: list[str],
    ) -> float:
        searchable_text = " ".join(
            [metadata.title, metadata.description, *metadata.keywords]
        )
        score = 20.0
        if any(_contains_phrase(metadata.title, phrase) for phrase in candidates):
            score += 25
        if any(
            _contains_phrase(metadata.description[:250], phrase)
            for phrase in candidates
        ):
            score += 20
        covered = sum(
            1 for phrase in candidates if _contains_phrase(searchable_text, phrase)
        )
        score += min(covered * 8, 20)
        if 5 <= len(metadata.keywords) <= 20:
            score += 10
        if 3 <= len(metadata.hashtags) <= 8:
            score += 5
        return round(min(score, 100.0), 1)

    def _description_score(self, description: str, candidates: list[str]) -> float:
        score = 25.0
        word_count = len(_words(description))
        if 25 <= word_count <= 160:
            score += 25
        elif word_count >= 15:
            score += 12
        if any(_contains_phrase(description[:250], phrase) for phrase in candidates):
            score += 25
        if any(term in _words(description.lower()) for term in ACTION_TERMS):
            score += 15
        if len(re.findall(r"[.!?]", description)) >= 2:
            score += 10
        return round(min(score, 100.0), 1)


def _candidate_phrases(topic: str, seed_keywords: list[str]) -> list[str]:
    phrases: list[str] = []
    for value in [topic, *seed_keywords]:
        normalized = " ".join(value.lower().split())
        if normalized and normalized not in phrases:
            phrases.append(normalized)
    return phrases


def _contains_phrase(text: str, phrase: str) -> bool:
    return phrase.lower() in text.lower()


def _words(value: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", value))
