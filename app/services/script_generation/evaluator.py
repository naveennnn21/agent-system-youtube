"""Evaluation logic for generated short-form scripts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.script_generation.models import ScriptDraft

WORDS_PER_SECOND = 2.45
MIN_SECONDS = 30
MAX_SECONDS = 60

CURIOSITY_TERMS = {
    "but",
    "secret",
    "surprising",
    "why",
    "what",
    "how",
    "mistake",
    "hidden",
    "instead",
}
RETENTION_TERMS = {
    "first",
    "second",
    "finally",
    "here",
    "because",
    "watch",
    "end",
    "before",
    "after",
}
SHARING_TERMS = {
    "share",
    "save",
    "send",
    "comment",
    "follow",
    "try",
}


@dataclass(slots=True)
class ScriptEvaluation:
    """Quality and compliance report for a generated script."""

    estimated_seconds: float
    word_count: int
    retention_score: float
    curiosity_score: float
    viral_score: float
    overall_score: float
    is_valid: bool
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class ScriptEvaluator:
    """Evaluate a script for length and Shorts-specific quality signals."""

    def evaluate(self, draft: ScriptDraft) -> ScriptEvaluation:
        words = _words(draft.full_text)
        word_count = len(words)
        estimated_seconds = round(word_count / WORDS_PER_SECOND, 1)

        curiosity_score = self._curiosity_score(draft)
        retention_score = self._retention_score(draft)
        viral_score = self._viral_score(draft)
        overall_score = round(
            (curiosity_score * 0.32)
            + (retention_score * 0.38)
            + (viral_score * 0.3),
            2,
        )

        issues: list[str] = []
        suggestions: list[str] = []
        if estimated_seconds < MIN_SECONDS:
            issues.append("Script is shorter than 30 seconds.")
            suggestions.append("Add one concrete example or contrast in the main script.")
        if estimated_seconds > MAX_SECONDS:
            issues.append("Script is longer than 60 seconds.")
            suggestions.append("Cut setup lines and keep only one core payoff.")
        if curiosity_score < 55:
            issues.append("Hook does not create enough curiosity.")
            suggestions.append("Open with a sharper contrast, question, or surprising claim.")
        if retention_score < 55:
            issues.append("Main script needs stronger retention structure.")
            suggestions.append("Add an open loop and resolve it near the end.")
        if viral_score < 45:
            issues.append("CTA or payoff is not share-oriented enough.")
            suggestions.append("Make the takeaway saveable, shareable, or comment-worthy.")

        return ScriptEvaluation(
            estimated_seconds=estimated_seconds,
            word_count=word_count,
            retention_score=retention_score,
            curiosity_score=curiosity_score,
            viral_score=viral_score,
            overall_score=overall_score,
            is_valid=not issues,
            issues=issues,
            suggestions=suggestions,
        )

    def _curiosity_score(self, draft: ScriptDraft) -> float:
        hook = draft.hook.lower()
        score = 35.0
        if "?" in draft.hook:
            score += 20
        if any(term in hook for term in CURIOSITY_TERMS):
            score += 25
        if 6 <= len(_words(draft.hook)) <= 24:
            score += 15
        if any(char.isdigit() for char in draft.hook):
            score += 5
        return min(score, 100.0)

    def _retention_score(self, draft: ScriptDraft) -> float:
        text = draft.script.lower()
        score = 30.0
        term_hits = sum(1 for term in RETENTION_TERMS if term in text)
        score += min(term_hits * 9, 35)
        sentence_count = max(1, len(re.findall(r"[.!?]", draft.script)))
        avg_words = len(_words(draft.script)) / sentence_count
        if avg_words <= 16:
            score += 15
        if any(term in text for term in {"but", "instead", "the catch", "here is"}):
            score += 15
        if len(_words(draft.script)) >= 55:
            score += 5
        return min(score, 100.0)

    def _viral_score(self, draft: ScriptDraft) -> float:
        full_text = draft.full_text.lower()
        cta = draft.cta.lower()
        score = 30.0
        if any(term in cta for term in SHARING_TERMS):
            score += 30
        if any(term in full_text for term in {"most people", "everyone", "nobody", "simple"}):
            score += 15
        if len(_words(draft.cta)) <= 18:
            score += 15
        if any(char.isdigit() for char in full_text):
            score += 10
        return min(score, 100.0)


def _words(value: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", value)
