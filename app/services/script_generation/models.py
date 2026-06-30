"""Data models for script generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ScriptGenerationRequest:
    """Input context for a short-form video script."""

    topic: str
    category: str = "general"
    keywords: list[str] = field(default_factory=list)
    target_seconds: int = 45
    audience: str = "curious general viewers"
    tone: str = "energetic, clear, and credible"
    research_context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ScriptDraft:
    """Public generated script contract."""

    hook: str
    script: str
    cta: str

    def to_dict(self) -> dict[str, str]:
        return {
            "hook": self.hook,
            "script": self.script,
            "cta": self.cta,
        }

    @property
    def full_text(self) -> str:
        return " ".join([self.hook.strip(), self.script.strip(), self.cta.strip()])
