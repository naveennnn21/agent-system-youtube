"""Claude-backed YouTube SEO Agent."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.config import Settings, get_settings
from app.services.seo import (
    ClaudeSEOClient,
    SEOEvaluation,
    SEOEvaluator,
    SEOGenerationRequest,
    SEOMetadata,
    SEOPromptBuilder,
)


class SEOGenerationError(RuntimeError):
    """Base error for SEO metadata generation."""


class SEOParsingError(SEOGenerationError):
    """Raised when model output cannot satisfy the public contract."""


class SEOProvider(Protocol):
    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        """Generate model text from rendered prompts."""


@dataclass(slots=True)
class SEOGenerationResult:
    """Generated metadata plus prompts and quality evaluation."""

    metadata: SEOMetadata
    evaluation: SEOEvaluation
    raw_text: str
    system_prompt: str
    user_prompt: str


class SEOAgent:
    """Generate optimized YouTube metadata with a stable output contract."""

    def __init__(
        self,
        *,
        provider: SEOProvider,
        prompt_builder: SEOPromptBuilder | None = None,
        evaluator: SEOEvaluator | None = None,
        title_max_length: int = 100,
        description_max_length: int = 5000,
        max_hashtags: int = 8,
        max_keywords: int = 20,
        strict: bool = False,
    ) -> None:
        self.provider = provider
        self.prompt_builder = prompt_builder or SEOPromptBuilder()
        self.evaluator = evaluator or SEOEvaluator()
        self.title_max_length = title_max_length
        self.description_max_length = description_max_length
        self.max_hashtags = max_hashtags
        self.max_keywords = max_keywords
        self.strict = strict

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "SEOAgent":
        """Create the production Claude-backed SEO agent."""
        settings = settings or get_settings()
        return cls(
            provider=ClaudeSEOClient(
                api_key=settings.ANTHROPIC_API_KEY,
                model=settings.CLAUDE_MODEL,
                base_url=settings.ANTHROPIC_BASE_URL,
                anthropic_version=settings.ANTHROPIC_VERSION,
                max_tokens=settings.CLAUDE_MAX_TOKENS,
                timeout=settings.CLAUDE_HTTP_TIMEOUT,
            ),
            evaluator=SEOEvaluator(minimum_score=settings.SEO_MIN_OVERALL_SCORE),
            title_max_length=settings.SEO_TITLE_MAX_LENGTH,
            description_max_length=settings.SEO_DESCRIPTION_MAX_LENGTH,
            max_hashtags=settings.SEO_MAX_HASHTAGS,
            max_keywords=settings.SEO_MAX_KEYWORDS,
        )

    async def generate_seo(
        self,
        request: SEOGenerationRequest,
    ) -> dict[str, str | list[str]]:
        """Return exactly ``title/description/hashtags/keywords``."""
        result = await self.generate(request)
        return result.metadata.to_dict()

    async def generate(self, request: SEOGenerationRequest) -> SEOGenerationResult:
        """Generate, normalize, and evaluate SEO metadata."""
        system_prompt, user_prompt = self.prompt_builder.build(request)
        raw_text = await self.provider.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        metadata = parse_seo_response(
            raw_text,
            title_max_length=self.title_max_length,
            description_max_length=self.description_max_length,
            max_hashtags=self.max_hashtags,
            max_keywords=self.max_keywords,
        )
        evaluation = self.evaluator.evaluate(
            metadata,
            topic=request.topic,
            seed_keywords=request.seed_keywords,
        )
        if self.strict and not evaluation.is_valid:
            raise SEOGenerationError(
                "Generated metadata did not pass SEO evaluation: "
                + "; ".join(evaluation.issues)
            )

        return SEOGenerationResult(
            metadata=metadata,
            evaluation=evaluation,
            raw_text=raw_text,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )


def parse_seo_response(
    raw_text: str,
    *,
    title_max_length: int = 100,
    description_max_length: int = 5000,
    max_hashtags: int = 8,
    max_keywords: int = 20,
) -> SEOMetadata:
    """Parse and normalize model JSON into the public SEO contract."""
    payload = _extract_json_payload(raw_text)
    missing = {"title", "description", "hashtags", "keywords"} - set(payload)
    if missing:
        raise SEOParsingError(f"SEO response missing keys: {sorted(missing)}")

    title = _clean_scalar(payload["title"], field_name="title")
    description = _clean_description(payload["description"])
    hashtags = _normalize_hashtags(payload["hashtags"])[:max_hashtags]
    keywords = _normalize_keywords(payload["keywords"])[:max_keywords]

    if not title or not description:
        raise SEOParsingError("SEO response contained an empty title or description.")
    if not hashtags or not keywords:
        raise SEOParsingError("SEO response must contain hashtags and keywords.")

    return SEOMetadata(
        title=_truncate_at_word(title, title_max_length),
        description=description[:description_max_length].rstrip(),
        hashtags=hashtags,
        keywords=keywords,
    )


def _extract_json_payload(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise SEOParsingError("SEO response was not JSON.") from None
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise SEOParsingError("SEO response contained invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise SEOParsingError("SEO response must be a JSON object.")
    return payload


def _clean_scalar(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise SEOParsingError(f"SEO {field_name} must be a string.")
    return " ".join(value.strip().strip("\"'").split())


def _clean_description(value: Any) -> str:
    if not isinstance(value, str):
        raise SEOParsingError("SEO description must be a string.")
    lines = [" ".join(line.split()) for line in value.strip().splitlines()]
    return "\n".join(line for line in lines if line)


def _coerce_list(value: Any, *, field_name: str) -> list[str]:
    if isinstance(value, str):
        items = re.split(r"[,\n]+", value)
    elif isinstance(value, list):
        items = value
    else:
        raise SEOParsingError(f"SEO {field_name} must be an array of strings.")
    if any(not isinstance(item, str) for item in items):
        raise SEOParsingError(f"SEO {field_name} must contain only strings.")
    return items


def _normalize_hashtags(value: Any) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in _coerce_list(value, field_name="hashtags"):
        body = re.sub(r"[^\w]", "", item.lstrip("#"), flags=re.UNICODE)
        key = body.casefold()
        if body and key not in seen:
            seen.add(key)
            normalized.append(f"#{body}")
    return normalized


def _normalize_keywords(value: Any) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in _coerce_list(value, field_name="keywords"):
        keyword = " ".join(item.lstrip("#").split()).strip(" ,;")
        key = keyword.casefold()
        if keyword and key not in seen:
            seen.add(key)
            normalized.append(keyword[:80].rstrip())
    return normalized


def _truncate_at_word(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    shortened = value[: limit + 1].rsplit(" ", 1)[0].rstrip(" -:|")
    return shortened or value[:limit].rstrip()
