from __future__ import annotations

import hashlib
import math
import time
from pathlib import Path

from runtime.controller.failure_codes import FailureCode
from runtime.observation.state_types import FrameEnvelope, FrameHealth, TransitionState


def _require_pillow():
    from PIL import Image, ImageStat

    return Image, ImageStat


def _file_hash(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _histogram_entropy(histogram: list[int]) -> float:
    total = sum(histogram)
    if total <= 0:
        return 0.0
    entropy = 0.0
    for value in histogram:
        if value == 0:
            continue
        probability = value / total
        entropy -= probability * math.log2(probability)
    return entropy


def analyze_image(
    path: str | Path,
    *,
    previous_hash: str | None = None,
    previous_seen_at: float | None = None,
    black_threshold: float,
    near_black_threshold: float,
    stale_timeout_s: float,
    now: float | None = None,
    source: str = "unknown",
) -> FrameEnvelope:
    Image, ImageStat = _require_pillow()
    image = Image.open(path).convert("L")
    width, height = image.size
    histogram = image.histogram()
    stat = ImageStat.Stat(image)
    mean_luma = float(stat.mean[0])
    variance = float(stat.var[0])
    entropy = _histogram_entropy(histogram)
    frame_hash = _file_hash(path)
    captured_at = now if now is not None else time.monotonic()
    is_black = mean_luma <= black_threshold
    is_near_black = mean_luma <= near_black_threshold
    is_repeated = previous_hash is not None and previous_hash == frame_hash
    is_stale = previous_seen_at is not None and (captured_at - previous_seen_at) >= stale_timeout_s

    failures: list[FailureCode] = []
    if is_black:
        failures.append(FailureCode.STREAM_BLACK_FRAME)
    elif is_near_black:
        failures.append(FailureCode.STREAM_NEAR_BLACK_FRAME)
    if is_repeated:
        failures.append(FailureCode.STREAM_REPEATED_FRAME)
    if is_stale:
        failures.append(FailureCode.STREAM_STALE_FRAME)

    return FrameEnvelope(
        path=Path(path),
        width=width,
        height=height,
        source=source,
        captured_at_monotonic=captured_at,
        frame_hash=frame_hash,
        health=FrameHealth(
            mean_luma=mean_luma,
            variance=variance,
            entropy=entropy,
            is_black=is_black,
            is_near_black=is_near_black,
            is_repeated=is_repeated,
            is_stale=is_stale,
            failures=tuple(failures),
        ),
        transition_state=TransitionState.UNKNOWN,
    )
