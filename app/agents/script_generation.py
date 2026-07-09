"""Claude-backed Script Generation Agent."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Protocol

from app.core.config import Settings, get_settings
from app.services.script_generation import (
    ClaudeScriptClient,
    ScriptDraft,
    ScriptEvaluation,
    ScriptEvaluator,
    ScriptGenerationRequest,
    ScriptPromptBuilder,
)

logger = logging.getLogger(__name__)


class ScriptGenerationError(RuntimeError):
    """Base error for script generation failures."""


class ScriptParsingError(ScriptGenerationError):
    """Raised when Claude output cannot be parsed into the contract."""


class ScriptProvider(Protocol):
    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        """Generate model text from rendered prompts."""


class ScriptGenerationAgent:
    """Generate 30-60 second YouTube Shorts scripts with Claude."""

    def __init__(
        self,
        *,
        provider: ScriptProvider,
        prompt_builder: ScriptPromptBuilder | None = None,
        evaluator: ScriptEvaluator | None = None,
        strict: bool = False,
    ) -> None:
        self.provider = provider
        self.prompt_builder = prompt_builder or ScriptPromptBuilder()
        self.evaluator = evaluator or ScriptEvaluator()
        self.strict = strict

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "ScriptGenerationAgent":
        """Create the production Claude-backed agent from settings."""
        settings = settings or get_settings()
        provider = ClaudeScriptClient(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.CLAUDE_MODEL,
            base_url=settings.ANTHROPIC_BASE_URL,
            anthropic_version=settings.ANTHROPIC_VERSION,
            max_tokens=settings.CLAUDE_MAX_TOKENS,
            timeout=settings.CLAUDE_HTTP_TIMEOUT,
        )
        return cls(provider=provider)

    async def generate_script(
        self,
        request: ScriptGenerationRequest,
    ) -> dict[str, str]:
        """Generate and return the public ``hook/script/cta`` contract."""
        result = await self.generate(request)
        return result.draft.to_dict()

    async def generate(
        self,
        request: ScriptGenerationRequest,
    ) -> "ScriptGenerationResult":
        """Generate a script and attach an evaluation report."""
        system_prompt, user_prompt = self.prompt_builder.build(request)
        raw_text = await self.provider.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        draft = parse_script_response(raw_text)
        evaluation = self.evaluator.evaluate(draft)

        if self.strict and not evaluation.is_valid:
            raise ScriptGenerationError(
                "Generated script did not pass evaluation: "
                + "; ".join(evaluation.issues)
            )

        return ScriptGenerationResult(
            draft=draft,
            evaluation=evaluation,
            raw_text=raw_text,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )


class ScriptGenerationResult:
    """Generation result with prompt and evaluation metadata."""

    def __init__(
        self,
        *,
        draft: ScriptDraft,
        evaluation: ScriptEvaluation,
        raw_text: str,
        system_prompt: str,
        user_prompt: str,
    ) -> None:
        self.draft = draft
        self.evaluation = evaluation
        self.raw_text = raw_text
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt


def parse_script_response(raw_text: str) -> ScriptDraft:
    """Parse Claude JSON output into a script draft."""
    payload = _extract_json_payload(raw_text)
    missing = {"hook", "script", "cta"} - set(payload)
    if missing:
        raise ScriptParsingError(
            f"Claude script response missing keys: {sorted(missing)}"
        )

    hook = _clean_text(payload["hook"])
    script = _clean_text(payload["script"])
    cta = _clean_text(payload["cta"])
    if not hook or not script or not cta:
        raise ScriptParsingError("Claude script response contained empty fields.")

    return ScriptDraft(hook=hook, script=script, cta=cta)


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
            raise ScriptParsingError("Claude script response was not JSON.") from None
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ScriptParsingError(
                "Claude script response contained invalid JSON."
            ) from exc

    if not isinstance(payload, dict):
        raise ScriptParsingError("Claude script response must be a JSON object.")
    return payload


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        raise ScriptParsingError("Claude script fields must be strings.")
    return re.sub(r"\s+", " ", value).strip()
