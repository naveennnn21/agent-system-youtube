"""MP3 duration estimation utilities."""

from __future__ import annotations

BITRATES = {
    (3, 3): [None, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],
    (3, 2): [None, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384],
    (3, 1): [None, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],
    (2, 3): [None, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256],
    (2, 2): [None, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
    (2, 1): [None, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
}

SAMPLE_RATES = {
    3: [44100, 48000, 32000],
    2: [22050, 24000, 16000],
    0: [11025, 12000, 8000],
}


def estimate_mp3_duration(content: bytes) -> float:
    """Estimate MP3 duration from MPEG audio frames.

    Returns ``0.0`` when the content does not contain parseable MP3 frames.
    """
    offset = _skip_id3v2(content)
    duration = 0.0
    frames = 0

    while offset + 4 <= len(content):
        header = int.from_bytes(content[offset : offset + 4], "big")
        frame = _parse_frame_header(header)
        if frame is None:
            offset += 1
            continue

        frame_length, samples_per_frame, sample_rate = frame
        if frame_length <= 0 or offset + frame_length > len(content) + 1:
            offset += 1
            continue

        duration += samples_per_frame / sample_rate
        frames += 1
        offset += frame_length

    if frames == 0:
        return 0.0
    return round(duration, 3)


def estimate_spoken_duration(text: str) -> float:
    """Fallback duration estimate for speech content."""
    words = [word for word in text.split() if word.strip()]
    return round(max(len(words) / 2.45, 0.1), 3)


def _skip_id3v2(content: bytes) -> int:
    if len(content) < 10 or content[:3] != b"ID3":
        return 0
    size = (
        ((content[6] & 0x7F) << 21)
        | ((content[7] & 0x7F) << 14)
        | ((content[8] & 0x7F) << 7)
        | (content[9] & 0x7F)
    )
    return 10 + size


def _parse_frame_header(header: int) -> tuple[int, int, int] | None:
    if ((header >> 21) & 0x7FF) != 0x7FF:
        return None

    version_id = (header >> 19) & 0x3
    layer_id = (header >> 17) & 0x3
    bitrate_index = (header >> 12) & 0xF
    sample_rate_index = (header >> 10) & 0x3
    padding = (header >> 9) & 0x1

    if version_id == 1 or layer_id == 0:
        return None
    if bitrate_index in {0, 0xF} or sample_rate_index == 0x3:
        return None

    version_key = 3 if version_id == 3 else 2
    bitrate = BITRATES.get((version_key, layer_id), [None])[bitrate_index]
    sample_rate = SAMPLE_RATES[version_id][sample_rate_index]
    if bitrate is None:
        return None

    bitrate_bps = bitrate * 1000
    if layer_id == 3:
        samples_per_frame = 384
        frame_length = int(((12 * bitrate_bps) / sample_rate + padding) * 4)
    else:
        samples_per_frame = 1152 if version_id == 3 or layer_id == 2 else 576
        coefficient = 144 if version_id == 3 else 72
        frame_length = int((coefficient * bitrate_bps) / sample_rate + padding)

    return frame_length, samples_per_frame, sample_rate
