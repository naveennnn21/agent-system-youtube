"""Filesystem audio storage."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path


class FileAudioStorage:
    """Store generated audio files on local disk."""

    def __init__(self, base_path: str | Path) -> None:
        self.base_path = Path(base_path)

    async def save(
        self,
        content: bytes,
        *,
        filename_prefix: str,
        extension: str = "mp3",
    ) -> str:
        if not content:
            raise ValueError("Audio content is empty.")

        today = datetime.now(UTC).strftime("%Y/%m/%d")
        directory = self.base_path / today
        directory.mkdir(parents=True, exist_ok=True)

        safe_prefix = _safe_filename(filename_prefix) or "voiceover"
        filename = f"{safe_prefix}-{uuid.uuid4().hex}.{extension.lstrip('.')}"
        path = directory / filename
        temp_path = path.with_suffix(f"{path.suffix}.tmp")
        temp_path.write_bytes(content)
        temp_path.replace(path)
        return str(path)


def _safe_filename(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower())
    return text.strip("-")[:80]
