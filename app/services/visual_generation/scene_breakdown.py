"""Scene breakdown from script text."""

from __future__ import annotations

import re

from app.services.visual_generation.models import SceneSpec, VisualGenerationRequest

WORDS_PER_SECOND = 2.45


class SceneBreakdownGenerator:
    """Convert a script into timed visual scenes."""

    def generate(self, request: VisualGenerationRequest) -> list[SceneSpec]:
        text = normalize_script_text(request.script)
        sentences = _split_sentences(text)
        if not sentences:
            raise ValueError("Script must contain text for visual generation.")

        target_scene_count = min(request.max_scenes, max(1, len(sentences)))
        groups = _group_sentences(sentences, target_scene_count)
        total_words = max(1, len(_words(text)))
        estimated_duration = max(30.0, min(60.0, total_words / WORDS_PER_SECOND))

        scenes: list[SceneSpec] = []
        elapsed = 0.0
        for index, group in enumerate(groups, start=1):
            narration = " ".join(group).strip()
            words = len(_words(narration))
            duration = max(3.0, estimated_duration * (words / total_words))
            start = round(elapsed, 2)
            end = round(min(estimated_duration, elapsed + duration), 2)
            if index == len(groups):
                end = round(estimated_duration, 2)

            keywords = _keywords(narration)
            scenes.append(
                SceneSpec(
                    index=index,
                    title=_scene_title(narration, index),
                    narration=narration,
                    start_seconds=start,
                    end_seconds=end,
                    visual_description=_visual_description(narration, request.topic),
                    keywords=keywords,
                )
            )
            elapsed = end

        return scenes


def normalize_script_text(script: str | dict[str, str]) -> str:
    """Flatten supported script inputs into one text block."""
    if isinstance(script, dict):
        return " ".join(
            value.strip()
            for key in ("hook", "script", "cta")
            if (value := script.get(key, ""))
        )
    return script.strip()


def _split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[.!?])\s+", text.strip())
    return [piece.strip() for piece in pieces if piece.strip()]


def _group_sentences(sentences: list[str], group_count: int) -> list[list[str]]:
    groups: list[list[str]] = [[] for _ in range(group_count)]
    for index, sentence in enumerate(sentences):
        groups[min(group_count - 1, index * group_count // len(sentences))].append(
            sentence
        )
    return [group for group in groups if group]


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", text)


def _keywords(text: str) -> list[str]:
    stopwords = {
        "about",
        "after",
        "and",
        "are",
        "because",
        "but",
        "for",
        "from",
        "into",
        "that",
        "the",
        "this",
        "with",
        "your",
    }
    seen: set[str] = set()
    keywords: list[str] = []
    for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]{2,}", text.lower()):
        if word in stopwords or word in seen:
            continue
        seen.add(word)
        keywords.append(word)
    return keywords[:8]


def _scene_title(narration: str, index: int) -> str:
    words = _words(narration)
    title = " ".join(words[:6]).strip()
    return title or f"Scene {index}"


def _visual_description(narration: str, topic: str) -> str:
    keywords = ", ".join(_keywords(narration)[:5])
    return (
        f"Vertical short-form scene about {topic}. Show the idea visually using "
        f"clear subject focus, expressive lighting, and visual keywords: {keywords}."
    )
