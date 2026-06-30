"""Script text normalization for editing and subtitles."""

from __future__ import annotations


def normalize_script_text(script: str | dict[str, str]) -> str:
    if isinstance(script, dict):
        return " ".join(
            value.strip()
            for key in ("hook", "script", "cta")
            if (value := script.get(key, ""))
        )
    return script.strip()
