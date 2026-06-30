"""Filesystem storage and image metadata extraction."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path


class FileVisualStorage:
    """Store generated visual assets on local disk."""

    def __init__(self, base_path: str | Path) -> None:
        self.base_path = Path(base_path)

    async def save(
        self,
        content: bytes,
        *,
        filename_prefix: str,
        extension: str,
    ) -> tuple[str, int | None, int | None]:
        if not content:
            raise ValueError("Visual asset content is empty.")

        today = datetime.now(UTC).strftime("%Y/%m/%d")
        directory = self.base_path / today
        directory.mkdir(parents=True, exist_ok=True)

        safe_prefix = _safe_filename(filename_prefix) or "visual"
        filename = f"{safe_prefix}-{uuid.uuid4().hex}.{extension.lstrip('.')}"
        path = directory / filename
        temp_path = path.with_suffix(f"{path.suffix}.tmp")
        temp_path.write_bytes(content)
        temp_path.replace(path)

        width, height = image_dimensions(content)
        return str(path), width, height


def image_dimensions(content: bytes) -> tuple[int | None, int | None]:
    """Return PNG/JPEG dimensions when parseable."""
    png = _png_dimensions(content)
    if png != (None, None):
        return png
    return _jpeg_dimensions(content)


def extension_from_media_type(media_type: str) -> str:
    value = media_type.lower()
    if "jpeg" in value or "jpg" in value:
        return "jpg"
    if "webp" in value:
        return "webp"
    return "png"


def _png_dimensions(content: bytes) -> tuple[int | None, int | None]:
    if len(content) < 24 or content[:8] != b"\x89PNG\r\n\x1a\n":
        return None, None
    if content[12:16] != b"IHDR":
        return None, None
    width = int.from_bytes(content[16:20], "big")
    height = int.from_bytes(content[20:24], "big")
    return width, height


def _jpeg_dimensions(content: bytes) -> tuple[int | None, int | None]:
    if len(content) < 4 or content[:2] != b"\xff\xd8":
        return None, None
    offset = 2
    while offset + 9 < len(content):
        if content[offset] != 0xFF:
            offset += 1
            continue
        marker = content[offset + 1]
        offset += 2
        if marker in {0xD8, 0xD9}:
            continue
        segment_length = int.from_bytes(content[offset : offset + 2], "big")
        if marker in {0xC0, 0xC1, 0xC2, 0xC3}:
            height = int.from_bytes(content[offset + 3 : offset + 5], "big")
            width = int.from_bytes(content[offset + 5 : offset + 7], "big")
            return width, height
        offset += segment_length
    return None, None


def _safe_filename(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower())
    return text.strip("-")[:80]
