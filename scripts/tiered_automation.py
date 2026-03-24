#!/usr/bin/env python3
"""Tier-2-first UI action scaffold for early live automation experiments.

This file now targets the first implementation slice from the runtime plan:

- `resolve` defaults to a Tier-2-first baseline.
- Tier 1 template matching remains available only as an explicit prototype path.
- `observe-act` provides a thin ADB-backed capture/act/capture loop.

Current scope: this file documents and implements contracts only. It is not a
trusted live runtime control plane by itself.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from time import sleep
from typing import Any, Literal
from urllib.parse import urljoin

import requests
try:
    from vlm_detector import VLMClient, locate_element
except ModuleNotFoundError:
    from scripts.vlm_detector import VLMClient, locate_element


DEFAULT_CACHE_PATH = Path("data/automation/tier1-cache.json")
DEFAULT_CACHE_THRESHOLD = 0.85
DEFAULT_MATCH_THRESHOLD = 0.86
DEFAULT_OBJECTIVE = "commission_collect"
DEFAULT_TIER2_MIN_CONFIDENCE = 0.84
DEFAULT_SETTLE_MS = 750
DEFAULT_CHANGE_THRESHOLD = 0.005
DEFAULT_CAPTURE_RETRIES = 3
DEFAULT_CAPTURE_RETRY_DELAY_MS = 150
DEFAULT_DROIDCAST_PORT = 53516


TierStatus = Literal["hit", "miss", "error"]
ActionType = Literal["TAP", "SWIPE", "WAIT"]
CaptureMethod = Literal["auto", "adb", "droidcast"]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _normalize_float(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _normalize_serial(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _load_cv_stack() -> tuple[Any, Any]:
    """Return (cv2, numpy) or raise a clear error."""

    try:
        import cv2
        import numpy as np
    except Exception as exc:
        raise RuntimeError(
            "Tier-1 requires OpenCV + numpy. Install with `uv sync --extra piloting` "
            "or `pip install opencv-python-headless numpy`."
        ) from exc
    return cv2, np


def _load_pillow():
    try:
        from PIL import Image
    except Exception as exc:
        raise RuntimeError(
            "A screenshot is required. Install Pillow with `uv sync --extra piloting` "
            "or `pip install Pillow`."
        ) from exc
    return Image


def _read_image_bytes(path: Path) -> bytes:
    with Path(path).open("rb") as handle:
        return handle.read()


@dataclass(frozen=True)
class Tier1Template:
    """Single deterministic action template."""

    entry_id: str
    template_path: str
    objective_tag: str
    action_type: ActionType
    target_norm_x: float
    target_norm_y: float
    match_threshold: float = DEFAULT_MATCH_THRESHOLD
    notes: str = ""
    hit_count: int = 0
    created_at: str = field(default_factory=_now_iso)
    last_hit_at: str | None = None

    @classmethod
    def from_manifest(cls, payload: dict[str, Any]) -> "Tier1Template":
        return cls(
            entry_id=str(payload["entry_id"]),
            template_path=str(payload["template_path"]),
            objective_tag=str(payload["objective_tag"]),
            action_type=payload["action_type"],
            target_norm_x=float(payload["target_norm_x"]),
            target_norm_y=float(payload["target_norm_y"]),
            match_threshold=float(payload.get("match_threshold", DEFAULT_MATCH_THRESHOLD)),
            notes=str(payload.get("notes", "")),
            hit_count=int(payload.get("hit_count", 0)),
            created_at=str(payload.get("created_at", _now_iso())),
            last_hit_at=payload.get("last_hit_at"),
        )

    def to_manifest(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Tier1Result:
    status: TierStatus
    reason: str
    best_score: float | None = None
    entry: Tier1Template | None = None
    action_type: ActionType | None = None
    normalized_coords: tuple[float, float] | None = None
    latency_ms: int = 0


@dataclass(frozen=True)
class Tier2Result:
    status: Literal["success", "no_result", "error"]
    reason: str
    action_type: ActionType = "TAP"
    normalized_coords: tuple[float, float] | None = None
    confidence: float | None = None
    bbox: tuple[int, int, int, int] | None = None
    attempt: int = 1
    model: str | None = None
    latency_ms: int = 0
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class ResolverResult:
    status: Literal["tier1_hit", "tier2_success", "tier2_escalate", "error"]
    screenshot: str
    objective_tag: str
    instruction: str
    tier1: Tier1Result
    tier2: Tier2Result | None = None
    selected_action_type: ActionType | None = None
    selected_coords: tuple[float, float] | None = None
    selected_from: str | None = None
    selected_reason: str | None = None

    def to_json(self) -> str:
        payload = asdict(self)
        if self.tier1.entry is not None:
            payload["tier1"]["entry"] = self.tier1.entry.to_manifest()
        if self.tier2 and self.tier2.raw is not None:
            payload["tier2"]["raw"] = self.tier2.raw
        return json.dumps(payload, indent=2)


@dataclass(frozen=True)
class ObserveActResult:
    status: Literal["executed_verified", "executed_unverified", "escalate", "error"]
    objective_tag: str
    instruction: str
    before_screenshot: str
    after_screenshot: str | None = None
    resolver: ResolverResult | None = None
    adb_serial: str | None = None
    pixel_coords: tuple[int, int] | None = None
    frame_changed: bool | None = None
    change_ratio: float | None = None
    reason: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


@dataclass(frozen=True)
class CaptureResult:
    status: Literal["success", "error"]
    method: str
    screenshot: str
    attempts: int
    reason: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


class Tier1TemplateCache:
    """Deterministic template cache with strict hit/miss policy."""

    def __init__(self, path: str | Path = DEFAULT_CACHE_PATH):
        self.path = Path(path).resolve()
        self.entries: list[Tier1Template] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self.entries = []
            return
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        raw_entries = payload.get("entries", [])
        self.entries = [Tier1Template.from_manifest(item) for item in raw_entries]

    def _write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "1.0",
            "updated_at": _now_iso(),
            "entry_count": len(self.entries),
            "entries": [entry.to_manifest() for entry in self.entries],
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @property
    def objectives(self) -> list[str]:
        return sorted(set(entry.objective_tag for entry in self.entries))

    def list_entries(self) -> list[dict[str, Any]]:
        return [entry.to_manifest() for entry in self.entries]

    def insert(
        self,
        template_path: str | Path,
        *,
        objective_tag: str,
        action_type: ActionType,
        target_norm_x: float,
        target_norm_y: float,
        entry_id: str | None = None,
        match_threshold: float = DEFAULT_MATCH_THRESHOLD,
        notes: str = "",
    ) -> Tier1Template:
        template = Path(template_path).resolve()
        if not template.is_file():
            raise FileNotFoundError(f"Template not found: {template}")

        entry = Tier1Template(
            entry_id=entry_id or f"{template.stem}-{int(datetime.now(UTC).timestamp())}",
            template_path=str(template),
            objective_tag=objective_tag.strip() or DEFAULT_OBJECTIVE,
            action_type=action_type,
            target_norm_x=_normalize_float(target_norm_x),
            target_norm_y=_normalize_float(target_norm_y),
            match_threshold=float(match_threshold),
            notes=notes.strip(),
        )
        self.entries.append(entry)
        self._write()
        return entry

    def lookup(self, screenshot_path: str | Path, *, objective_tag: str, min_threshold: float = DEFAULT_CACHE_THRESHOLD) -> Tier1Result:
        start = perf_counter()
        image_path = Path(screenshot_path)
        if not image_path.is_file():
            return Tier1Result(status="error", reason=f"Screenshot missing: {image_path}", latency_ms=0)

        try:
            cv2, np = _load_cv_stack()
            Image = _load_pillow()
        except Exception as exc:
            return Tier1Result(
                status="miss",
                reason=f"tier1_dependencies_missing:{exc}",
                latency_ms=int((perf_counter() - start) * 1000),
            )

        try:
            candidates = [entry for entry in self.entries if entry.objective_tag == objective_tag]
            if not candidates:
                return Tier1Result(status="miss", reason="no_entries_for_objective", latency_ms=0)

            target = np.asarray(Image.open(image_path).convert("L"))
            if target.size == 0:
                return Tier1Result(status="error", reason="empty_screenshot", latency_ms=0)

            best_score = -1.0
            best_entry = None

            for entry in candidates:
                template_image = np.asarray(Image.open(entry.template_path).convert("L"))
                if template_image.size == 0 or template_image.shape[0] > target.shape[0] or template_image.shape[1] > target.shape[1]:
                    continue

                result = cv2.matchTemplate(target, template_image, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, _, _ = cv2.minMaxLoc(result)
                score = float(max_val)
                if score <= best_score:
                    continue

                threshold = max(min_threshold, entry.match_threshold)
                if score >= threshold:
                    best_score = score
                    best_entry = entry

            if best_entry is None or best_score <= 0:
                return Tier1Result(
                    status="miss",
                    reason="no_match_above_threshold",
                    latency_ms=int((perf_counter() - start) * 1000),
                )

            updated = Tier1Template(
                entry_id=best_entry.entry_id,
                template_path=best_entry.template_path,
                objective_tag=best_entry.objective_tag,
                action_type=best_entry.action_type,
                target_norm_x=best_entry.target_norm_x,
                target_norm_y=best_entry.target_norm_y,
                match_threshold=best_entry.match_threshold,
                notes=best_entry.notes,
                hit_count=best_entry.hit_count + 1,
                created_at=best_entry.created_at,
                last_hit_at=_now_iso(),
            )

            self.entries = [
                updated if item.entry_id == best_entry.entry_id else item for item in self.entries
            ]
            self._write()

            return Tier1Result(
                status="hit",
                reason="template_match",
                best_score=best_score,
                entry=updated,
                action_type=updated.action_type,
                normalized_coords=(updated.target_norm_x, updated.target_norm_y),
                latency_ms=int((perf_counter() - start) * 1000),
            )
        except Exception as exc:  # defensive: keep single failure mode for callers.
            return Tier1Result(
                status="error",
                reason=f"tier1_failed: {exc}",
                latency_ms=int((perf_counter() - start) * 1000),
            )


def _bbox_to_normalized(
    bbox: list[int] | tuple[int, int, int, int],
    width: int,
    height: int,
) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    cx = ((x1 + x2) / 2) / max(1, width)
    cy = ((y1 + y2) / 2) / max(1, height)
    return (_normalize_float(cx), _normalize_float(cy))


def _bbox_is_reasonable(
    bbox: list[int] | tuple[int, int, int, int],
    *,
    width: int,
    height: int,
) -> bool:
    x1, y1, x2, y2 = bbox
    if x2 <= x1 or y2 <= y1:
        return False
    if not (0 <= x1 <= width and 0 <= x2 <= width):
        return False
    if not (0 <= y1 <= height and 0 <= y2 <= height):
        return False
    area = (x2 - x1) * (y2 - y1)
    return area > 2


class Tier2Router:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        *,
        min_confidence: float = DEFAULT_TIER2_MIN_CONFIDENCE,
    ):
        self.base_url = base_url or os.getenv("SC_VLM_BASE_URL", "http://localhost:18900/v1")
        self.model = model or os.getenv("SC_VLM_MODEL", "local-vlm")
        self.min_confidence = min_confidence
        self.client = VLMClient(base_url=self.base_url, model=self.model)

    def locate(
        self,
        screenshot: str | Path,
        instruction: str,
        *,
        task_context: str,
        attempt: int = 1,
        previous_attempts: list[dict[str, Any]] | None = None,
    ) -> Tier2Result:
        start = perf_counter()
        image = Path(screenshot)
        if not image.is_file():
            return Tier2Result(
                status="error",
                reason=f"screenshot_missing:{image}",
                attempt=attempt,
                latency_ms=int((perf_counter() - start) * 1000),
            )

        try:
            from PIL import Image
        except Exception as exc:
            return Tier2Result(
                status="error",
                reason=f"tier2_dependency_missing:{exc}",
                attempt=attempt,
                latency_ms=int((perf_counter() - start) * 1000),
            )

        try:
            width, height = Image.open(image).size
            target = instruction
            if previous_attempts:
                target = (
                    f"{instruction}. "
                    f"Previous attempts: {json.dumps(previous_attempts)}. "
                    "Try a different likely location if any earlier hit was uncertain."
                )

            payload = locate_element(
                image,
                target=target,
                task_context=task_context,
                client=self.client,
            )
        except Exception as exc:
            return Tier2Result(
                status="error",
                reason=f"tier2_exception:{exc}",
                attempt=attempt,
                model=self.model,
                latency_ms=int((perf_counter() - start) * 1000),
            )

        result = payload.get("result", {})
        found = bool(result.get("found"))
        if not found:
            return Tier2Result(
                status="no_result",
                reason="not_found",
                attempt=attempt,
                model=self.model,
                confidence=float(result.get("confidence", 0.0)),
                raw=result,
                latency_ms=int((perf_counter() - start) * 1000),
            )

        bbox = result.get("bbox")
        confidence = result.get("confidence")
        if not isinstance(confidence, (int, float)):
            confidence = 0.0
        if not isinstance(bbox, list) or len(bbox) != 4:
            return Tier2Result(
                status="no_result",
                reason="invalid_bbox",
                attempt=attempt,
                model=self.model,
                confidence=float(confidence),
                raw=result,
                latency_ms=int((perf_counter() - start) * 1000),
            )
        box_tuple = tuple(int(round(v)) for v in bbox)
        if not _bbox_is_reasonable(box_tuple, width=width, height=height):
            return Tier2Result(
                status="no_result",
                reason="bbox_out_of_bounds_or_tiny",
                attempt=attempt,
                model=self.model,
                confidence=float(confidence),
                raw=result,
                latency_ms=int((perf_counter() - start) * 1000),
            )
        if confidence < self.min_confidence:
            return Tier2Result(
                status="no_result",
                reason="low_confidence",
                attempt=attempt,
                model=self.model,
                confidence=float(confidence),
                bbox=box_tuple,
                raw=result,
                latency_ms=int((perf_counter() - start) * 1000),
            )

        x, y = _bbox_to_normalized(box_tuple, width=width, height=height)
        return Tier2Result(
            status="success",
            reason="found_location",
            action_type="TAP",
            normalized_coords=(x, y),
            confidence=float(confidence),
            bbox=box_tuple,
            attempt=attempt,
            model=self.model,
            raw=result,
            latency_ms=int((perf_counter() - start) * 1000),
        )


def _default_adb_serial() -> str | None:
    env_value = os.getenv("SC_ADB_SERIAL")
    if env_value:
        return env_value
    payload = _load_runtime_config(None)
    if payload is None:
        return None
    serial = payload.get("adb_serial")
    return str(serial) if serial else None


def _load_runtime_config(config_path: str | Path | None) -> dict[str, Any] | None:
    if config_path is not None:
        candidate = Path(config_path)
    else:
        candidate = Path("configs/memu.json")
    if not candidate.is_file():
        return None
    try:
        return json.loads(candidate.read_text(encoding="utf-8"))
    except Exception:
        return None


def _default_capture_method(config_path: str | Path | None) -> CaptureMethod:
    env_value = os.getenv("SC_SCREENSHOT_METHOD")
    if env_value in {"adb", "droidcast"}:
        return env_value
    payload = _load_runtime_config(config_path)
    if payload is None:
        return "adb"
    method = str(payload.get("screenshot_method", "adb")).lower()
    if method == "droidcast":
        return "droidcast"
    return "adb"


def _default_droidcast_base_url(config_path: str | Path | None) -> str | None:
    env_value = os.getenv("SC_DROIDCAST_URL")
    if env_value:
        return env_value.rstrip("/")
    payload = _load_runtime_config(config_path)
    if payload is None:
        return None
    ports = payload.get("ports") or {}
    port = ports.get("droidcast")
    if port is None:
        return None
    return f"http://127.0.0.1:{port}"


def _default_droidcast_port(config_path: str | Path | None) -> int:
    payload = _load_runtime_config(config_path)
    if payload is None:
        return DEFAULT_DROIDCAST_PORT
    ports = payload.get("ports") or {}
    port = ports.get("droidcast")
    try:
        return int(port)
    except Exception:
        return DEFAULT_DROIDCAST_PORT


class ADBExecutor:
    def __init__(self, serial: str | None = None):
        self.serial = _normalize_serial(serial) or _default_adb_serial()

    def _cmd(self, *parts: str) -> list[str]:
        cmd = ["adb"]
        if self.serial:
            cmd.extend(["-s", self.serial])
        cmd.extend(parts)
        return cmd

    def tap(
        self,
        normalized_coords: tuple[float, float],
        *,
        screenshot_path: str | Path,
        jitter_px: int = 0,
    ) -> tuple[int, int]:
        Image = _load_pillow()
        width, height = Image.open(screenshot_path).size
        x = int(round(normalized_coords[0] * width))
        y = int(round(normalized_coords[1] * height))
        if jitter_px > 0:
            x += random.randint(-jitter_px, jitter_px)
            y += random.randint(-jitter_px, jitter_px)
        x = max(0, min(width - 1, x))
        y = max(0, min(height - 1, y))
        subprocess.run(self._cmd("shell", "input", "tap", str(x), str(y)), check=True)
        return (x, y)


class ADBCaptureProvider:
    def __init__(self, serial: str | None = None):
        self.executor = ADBExecutor(serial=serial)

    @property
    def method_name(self) -> str:
        return "adb"

    def screenshot(self, output_path: str | Path) -> Path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            subprocess.run(
                self.executor._cmd("exec-out", "screencap", "-p"),
                check=True,
                stdout=handle,
            )
        return target


class DroidCastCaptureProvider:
    def __init__(
        self,
        base_url: str,
        *,
        serial: str | None = None,
        local_port: int | None = None,
        remote_port: int | None = None,
        timeout_s: int = 10,
    ):
        self.base_url = base_url.rstrip("/")
        self.serial = _normalize_serial(serial)
        self.local_port = local_port
        self.remote_port = remote_port
        self.timeout_s = timeout_s

    @property
    def method_name(self) -> str:
        return "droidcast"

    def _candidate_urls(self) -> list[str]:
        env_paths = os.getenv("SC_DROIDCAST_PATHS")
        if env_paths:
            suffixes = [item.strip().lstrip("/") for item in env_paths.split(",") if item.strip()]
        else:
            suffixes = ["screenshot", "preview", ""]
        urls: list[str] = []
        for suffix in suffixes:
            url = self.base_url if not suffix else urljoin(f"{self.base_url}/", suffix)
            if url not in urls:
                urls.append(url)
        return urls

    def _ensure_forward(self) -> None:
        if self.serial is None or self.local_port is None or self.remote_port is None:
            return
        subprocess.run(
            [
                "adb",
                "-s",
                self.serial,
                "forward",
                f"tcp:{self.local_port}",
                f"tcp:{self.remote_port}",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def screenshot(self, output_path: str | Path) -> Path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        last_error: str | None = None
        self._ensure_forward()
        for url in self._candidate_urls():
            try:
                response = requests.get(url, timeout=self.timeout_s)
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "")
                content = response.content
                if not (content_type.startswith("image/") or content.startswith(b"\x89PNG")):
                    last_error = f"non_image_response:{url}:{content_type or 'unknown'}"
                    continue
                target.write_bytes(content)
                return target
            except Exception as exc:
                last_error = f"{url}:{exc}"
                continue
        raise RuntimeError(f"droidcast_capture_failed:{last_error or 'no_candidate_urls'}")


def _build_capture_provider(
    *,
    capture_method: CaptureMethod,
    adb_serial: str | None,
    droidcast_url: str | None,
    config_path: str | Path | None,
):
    effective_method = capture_method
    if effective_method == "auto":
        effective_method = _default_capture_method(config_path)
    if effective_method == "adb":
        return ADBCaptureProvider(serial=adb_serial)
    base_url = droidcast_url or _default_droidcast_base_url(config_path)
    if not base_url:
        raise RuntimeError("droidcast_requested_but_no_base_url_configured")
    local_port = _default_droidcast_port(config_path)
    return DroidCastCaptureProvider(
        base_url=base_url,
        serial=adb_serial,
        local_port=local_port,
        remote_port=local_port,
    )


def _screenshot_is_usable(image_path: str | Path) -> tuple[bool, str | None]:
    Image = _load_pillow()
    image = Image.open(image_path).convert("L")
    width, height = image.size
    if width < 32 or height < 32:
        return (False, f"image_too_small:{width}x{height}")
    low, high = image.getextrema()
    if high - low < 4:
        return (False, f"near_uniform_frame:{low}:{high}")
    return (True, None)


def capture_screenshot(
    *,
    output_path: str | Path,
    capture_method: CaptureMethod,
    adb_serial: str | None,
    droidcast_url: str | None,
    config_path: str | Path | None,
    retries: int = DEFAULT_CAPTURE_RETRIES,
    retry_delay_ms: int = DEFAULT_CAPTURE_RETRY_DELAY_MS,
) -> CaptureResult:
    provider = _build_capture_provider(
        capture_method=capture_method,
        adb_serial=adb_serial,
        droidcast_url=droidcast_url,
        config_path=config_path,
    )
    target = Path(output_path)
    last_reason: str | None = None
    attempts = max(1, retries)
    for attempt in range(1, attempts + 1):
        try:
            provider.screenshot(target)
            usable, reason = _screenshot_is_usable(target)
            if usable:
                return CaptureResult(
                    status="success",
                    method=provider.method_name,
                    screenshot=str(target),
                    attempts=attempt,
                )
            last_reason = reason
        except Exception as exc:
            last_reason = str(exc)
        if attempt < attempts:
            sleep(max(0, retry_delay_ms) / 1000)
    return CaptureResult(
        status="error",
        method=provider.method_name,
        screenshot=str(target),
        attempts=attempts,
        reason=last_reason or "capture_failed",
    )


def _frame_change_ratio(before_path: str | Path, after_path: str | Path) -> float:
    Image = _load_pillow()
    before = Image.open(before_path).convert("RGB")
    after = Image.open(after_path).convert("RGB")
    if before.size != after.size:
        return 1.0
    before_pixels = before.load()
    after_pixels = after.load()
    changed = 0
    total = before.size[0] * before.size[1]
    for y in range(before.size[1]):
        for x in range(before.size[0]):
            if before_pixels[x, y] != after_pixels[x, y]:
                changed += 1
    return changed / max(1, total)


def resolve(
    screenshot: str | Path,
    *,
    objective_tag: str,
    instruction: str,
    cache_path: str | Path = DEFAULT_CACHE_PATH,
    cache_threshold: float = DEFAULT_CACHE_THRESHOLD,
    tier2_base_url: str | None = None,
    tier2_model: str | None = None,
    tier2_retry: bool = False,
    task_context: str = DEFAULT_OBJECTIVE,
    use_template_cache: bool = False,
) -> ResolverResult:
    if use_template_cache:
        cache = Tier1TemplateCache(cache_path)
        tier1 = cache.lookup(screenshot, objective_tag=objective_tag, min_threshold=cache_threshold)

        if tier1.status == "hit" and tier1.entry is not None and tier1.normalized_coords is not None:
            return ResolverResult(
                status="tier1_hit",
                screenshot=str(Path(screenshot)),
                objective_tag=objective_tag,
                instruction=instruction,
                tier1=tier1,
                selected_action_type=tier1.action_type,
                selected_coords=tier1.normalized_coords,
                selected_from="tier1",
                selected_reason="template_match",
            )

        if tier1.status == "error":
            return ResolverResult(
                status="error",
                screenshot=str(Path(screenshot)),
                objective_tag=objective_tag,
                instruction=instruction,
                tier1=tier1,
                selected_reason=tier1.reason,
            )
    else:
        tier1 = Tier1Result(
            status="miss",
            reason="tier1_disabled_phase1_tier2_baseline",
            latency_ms=0,
        )

    tier2 = Tier2Router(base_url=tier2_base_url, model=tier2_model)
    first = tier2.locate(
        screenshot,
        instruction,
        task_context=task_context,
        attempt=1,
    )
    if first.status == "error":
        return ResolverResult(
            status="error",
            screenshot=str(Path(screenshot)),
            objective_tag=objective_tag,
            instruction=instruction,
            tier1=tier1,
            tier2=first,
            selected_reason=first.reason,
        )
    if first.status == "success" and first.normalized_coords is not None:
        return ResolverResult(
            status="tier2_success",
            screenshot=str(Path(screenshot)),
            objective_tag=objective_tag,
            instruction=instruction,
            tier1=tier1,
            tier2=first,
            selected_action_type=first.action_type,
            selected_coords=first.normalized_coords,
            selected_from="tier2",
            selected_reason="grounded_by_vlm",
        )

    if not tier2_retry:
        return ResolverResult(
            status="tier2_escalate",
            screenshot=str(Path(screenshot)),
            objective_tag=objective_tag,
            instruction=instruction,
            tier1=tier1,
            tier2=first,
            selected_reason=first.reason,
        )

    second = tier2.locate(
        screenshot,
        f"{instruction} with full-screen search and no assumptions.",
        task_context=task_context,
        attempt=2,
        previous_attempts=[{
            "attempt": 1,
            "status": first.status,
            "reason": first.reason,
            "confidence": first.confidence,
        }],
    )
    if second.status == "error":
        return ResolverResult(
            status="error",
            screenshot=str(Path(screenshot)),
            objective_tag=objective_tag,
            instruction=instruction,
            tier1=tier1,
            tier2=second,
            selected_reason=second.reason,
        )
    if second.status == "success" and second.normalized_coords is not None:
        return ResolverResult(
            status="tier2_success",
            screenshot=str(Path(screenshot)),
            objective_tag=objective_tag,
            instruction=instruction,
            tier1=tier1,
            tier2=second,
            selected_action_type=second.action_type,
            selected_coords=second.normalized_coords,
            selected_from="tier2_retry",
            selected_reason="grounded_by_vlm_retry",
        )

    return ResolverResult(
        status="tier2_escalate",
        screenshot=str(Path(screenshot)),
        objective_tag=objective_tag,
        instruction=instruction,
        tier1=tier1,
        tier2=second,
        selected_reason=f"{first.reason};{second.reason}",
    )


def observe_act(
    *,
    instruction: str,
    objective_tag: str,
    task_context: str,
    adb_serial: str | None,
    capture_method: CaptureMethod,
    droidcast_url: str | None,
    config_path: str | Path | None,
    output_dir: str | Path | None,
    settle_ms: int,
    change_threshold: float,
    jitter_px: int,
    capture_retries: int,
    capture_retry_delay_ms: int,
    cache_path: str | Path,
    cache_threshold: float,
    tier2_base_url: str | None,
    tier2_model: str | None,
    tier2_retry: bool,
    use_template_cache: bool,
) -> ObserveActResult:
    if output_dir is None:
        base_dir = Path(tempfile.mkdtemp(prefix="tiered-automation-"))
    else:
        base_dir = Path(output_dir)
        base_dir.mkdir(parents=True, exist_ok=True)

    adb = ADBExecutor(serial=adb_serial)
    before_capture = capture_screenshot(
        output_path=base_dir / "before.png",
        capture_method=capture_method,
        adb_serial=adb_serial,
        droidcast_url=droidcast_url,
        config_path=config_path,
        retries=capture_retries,
        retry_delay_ms=capture_retry_delay_ms,
    )
    if before_capture.status != "success":
        return ObserveActResult(
            status="error",
            objective_tag=objective_tag,
            instruction=instruction,
            before_screenshot=before_capture.screenshot,
            adb_serial=adb.serial,
            reason=f"initial_capture_failed:{before_capture.reason}",
        )
    before_path = Path(before_capture.screenshot)
    resolver = resolve(
        before_path,
        objective_tag=objective_tag,
        instruction=instruction,
        cache_path=cache_path,
        cache_threshold=cache_threshold,
        tier2_base_url=tier2_base_url,
        tier2_model=tier2_model,
        tier2_retry=tier2_retry,
        task_context=task_context,
        use_template_cache=use_template_cache,
    )

    if resolver.status not in {"tier1_hit", "tier2_success"} or resolver.selected_coords is None:
        return ObserveActResult(
            status="escalate" if resolver.status == "tier2_escalate" else "error",
            objective_tag=objective_tag,
            instruction=instruction,
            before_screenshot=str(before_path),
            resolver=resolver,
            adb_serial=adb.serial,
            reason=resolver.selected_reason,
        )

    if resolver.selected_action_type != "TAP":
        return ObserveActResult(
            status="error",
            objective_tag=objective_tag,
            instruction=instruction,
            before_screenshot=str(before_path),
            resolver=resolver,
            adb_serial=adb.serial,
            reason=f"unsupported_action_type:{resolver.selected_action_type}",
        )

    try:
        pixel_coords = adb.tap(
            resolver.selected_coords,
            screenshot_path=before_path,
            jitter_px=jitter_px,
        )
        sleep(max(0, settle_ms) / 1000)
        after_capture = capture_screenshot(
            output_path=base_dir / "after.png",
            capture_method=capture_method,
            adb_serial=adb_serial,
            droidcast_url=droidcast_url,
            config_path=config_path,
            retries=capture_retries,
            retry_delay_ms=capture_retry_delay_ms,
        )
        if after_capture.status != "success":
            raise RuntimeError(f"followup_capture_failed:{after_capture.reason}")
        after_path = Path(after_capture.screenshot)
        ratio = _frame_change_ratio(before_path, after_path)
    except Exception as exc:
        return ObserveActResult(
            status="error",
            objective_tag=objective_tag,
            instruction=instruction,
            before_screenshot=str(before_path),
            resolver=resolver,
            adb_serial=adb.serial,
            pixel_coords=locals().get("pixel_coords"),
            reason=f"observe_act_failed:{exc}",
        )

    changed = ratio >= change_threshold
    return ObserveActResult(
        status="executed_verified" if changed else "executed_unverified",
        objective_tag=objective_tag,
        instruction=instruction,
        before_screenshot=str(before_path),
        after_screenshot=str(after_path),
        resolver=resolver,
        adb_serial=adb.serial,
        pixel_coords=pixel_coords,
        frame_changed=changed,
        change_ratio=ratio,
        reason="frame_changed" if changed else "frame_change_below_threshold",
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tier-2-first automation scaffold.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    resolve_parser = subparsers.add_parser("resolve", help="Resolve one screenshot to an action recommendation.")
    resolve_parser.add_argument("screenshot", help="Primary screenshot path.")
    resolve_parser.add_argument("--objective-tag", default=DEFAULT_OBJECTIVE, help="Objective namespace for resolution.")
    resolve_parser.add_argument("--instruction", required=True, help="Action instruction for Tier-2 grounding.")
    resolve_parser.add_argument("--task-context", default="commission_collect", help="Task context text for Tier-2 model.")
    resolve_parser.add_argument("--cache-path", default=str(DEFAULT_CACHE_PATH), help="Path to Tier-1 prototype cache manifest.")
    resolve_parser.add_argument("--cache-threshold", type=float, default=DEFAULT_CACHE_THRESHOLD)
    resolve_parser.add_argument("--tier2-base-url", default=None, help="Optional VLM endpoint override.")
    resolve_parser.add_argument("--tier2-model", default=None, help="Optional model override.")
    resolve_parser.add_argument("--retry", action="store_true", help="Do a second Tier-2 attempt with retry prompt.")
    resolve_parser.add_argument("--use-template-cache", action="store_true", help="Opt into the prototype Tier-1 template cache.")

    lookup_parser = subparsers.add_parser("lookup", help="Run only Tier-1 lookup against cache.")
    lookup_parser.add_argument("screenshot", help="Screenshot path.")
    lookup_parser.add_argument("--objective-tag", default=DEFAULT_OBJECTIVE)
    lookup_parser.add_argument("--cache-path", default=str(DEFAULT_CACHE_PATH))
    lookup_parser.add_argument("--cache-threshold", type=float, default=DEFAULT_CACHE_THRESHOLD)

    register_parser = subparsers.add_parser("register", help="Add one template into Tier-1 cache.")
    register_parser.add_argument("template", help="Template image path.")
    register_parser.add_argument("--objective-tag", default=DEFAULT_OBJECTIVE)
    register_parser.add_argument("--cache-path", default=str(DEFAULT_CACHE_PATH))
    register_parser.add_argument("--entry-id", default=None)
    register_parser.add_argument("--action-type", default="TAP", choices=["TAP", "SWIPE", "WAIT"])
    register_parser.add_argument("--target-norm-x", type=float, required=True)
    register_parser.add_argument("--target-norm-y", type=float, required=True)
    register_parser.add_argument("--match-threshold", type=float, default=DEFAULT_MATCH_THRESHOLD)
    register_parser.add_argument("--notes", default="")

    observe_parser = subparsers.add_parser("observe-act", help="Capture, resolve, act, and capture again via ADB.")
    observe_parser.add_argument("--instruction", required=True, help="Action instruction for Tier-2 grounding.")
    observe_parser.add_argument("--objective-tag", default=DEFAULT_OBJECTIVE)
    observe_parser.add_argument("--task-context", default=DEFAULT_OBJECTIVE)
    observe_parser.add_argument("--adb-serial", default=_default_adb_serial(), help="ADB serial override.")
    observe_parser.add_argument("--capture-method", default="auto", choices=["auto", "adb", "droidcast"], help="Screenshot transport override.")
    observe_parser.add_argument("--config-path", default="configs/memu.json", help="Runtime config used for default transport selection.")
    observe_parser.add_argument("--droidcast-url", default=None, help="Optional full DroidCast base URL override.")
    observe_parser.add_argument("--output-dir", default=None, help="Optional directory for before/after screenshots.")
    observe_parser.add_argument("--settle-ms", type=int, default=DEFAULT_SETTLE_MS, help="Delay between action and follow-up capture.")
    observe_parser.add_argument("--change-threshold", type=float, default=DEFAULT_CHANGE_THRESHOLD, help="Minimum pixel-change ratio to treat follow-up as changed.")
    observe_parser.add_argument("--jitter-px", type=int, default=3, help="Optional pixel jitter applied to taps.")
    observe_parser.add_argument("--capture-retries", type=int, default=DEFAULT_CAPTURE_RETRIES, help="How many times to retry screenshot capture.")
    observe_parser.add_argument("--capture-retry-delay-ms", type=int, default=DEFAULT_CAPTURE_RETRY_DELAY_MS, help="Delay between screenshot retries.")
    observe_parser.add_argument("--cache-path", default=str(DEFAULT_CACHE_PATH))
    observe_parser.add_argument("--cache-threshold", type=float, default=DEFAULT_CACHE_THRESHOLD)
    observe_parser.add_argument("--tier2-base-url", default=None)
    observe_parser.add_argument("--tier2-model", default=None)
    observe_parser.add_argument("--retry", action="store_true")
    observe_parser.add_argument("--use-template-cache", action="store_true", help="Opt into the prototype Tier-1 template cache.")

    capture_parser = subparsers.add_parser("capture", help="Capture one validated screenshot via the configured transport.")
    capture_parser.add_argument("--output", required=True, help="Screenshot output path.")
    capture_parser.add_argument("--adb-serial", default=_default_adb_serial(), help="ADB serial override.")
    capture_parser.add_argument("--capture-method", default="auto", choices=["auto", "adb", "droidcast"], help="Screenshot transport override.")
    capture_parser.add_argument("--config-path", default="configs/memu.json", help="Runtime config used for default transport selection.")
    capture_parser.add_argument("--droidcast-url", default=None, help="Optional full DroidCast base URL override.")
    capture_parser.add_argument("--capture-retries", type=int, default=DEFAULT_CAPTURE_RETRIES)
    capture_parser.add_argument("--capture-retry-delay-ms", type=int, default=DEFAULT_CAPTURE_RETRY_DELAY_MS)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command == "lookup":
        cache = Tier1TemplateCache(args.cache_path)
        result = cache.lookup(args.screenshot, objective_tag=args.objective_tag, min_threshold=args.cache_threshold)
        print(json.dumps({
            "status": result.status,
            "reason": result.reason,
            "best_score": result.best_score,
            "entry": result.entry.to_manifest() if result.entry else None,
            "normalized_coords": result.normalized_coords,
            "latency_ms": result.latency_ms,
        }, indent=2))
        return 0 if result.status in {"hit", "miss"} else 2

    if args.command == "register":
        cache = Tier1TemplateCache(args.cache_path)
        entry = cache.insert(
            args.template,
            objective_tag=args.objective_tag,
            action_type=args.action_type,
            target_norm_x=args.target_norm_x,
            target_norm_y=args.target_norm_y,
            entry_id=args.entry_id,
            match_threshold=args.match_threshold,
            notes=args.notes,
        )
        print(json.dumps(entry.to_manifest(), indent=2))
        return 0

    if args.command == "resolve":
        result = resolve(
            args.screenshot,
            objective_tag=args.objective_tag,
            instruction=args.instruction,
            cache_path=args.cache_path,
            cache_threshold=args.cache_threshold,
            tier2_base_url=args.tier2_base_url,
            tier2_model=args.tier2_model,
            tier2_retry=args.retry,
            task_context=args.task_context,
            use_template_cache=args.use_template_cache,
        )
        print(result.to_json())
        if result.status in {"tier1_hit", "tier2_success"}:
            return 0
        if result.status == "tier2_escalate":
            return 1
        return 2

    if args.command == "observe-act":
        result = observe_act(
            instruction=args.instruction,
            objective_tag=args.objective_tag,
            task_context=args.task_context,
            adb_serial=args.adb_serial,
            capture_method=args.capture_method,
            droidcast_url=args.droidcast_url,
            config_path=args.config_path,
            output_dir=args.output_dir,
            settle_ms=args.settle_ms,
            change_threshold=args.change_threshold,
            jitter_px=args.jitter_px,
            capture_retries=args.capture_retries,
            capture_retry_delay_ms=args.capture_retry_delay_ms,
            cache_path=args.cache_path,
            cache_threshold=args.cache_threshold,
            tier2_base_url=args.tier2_base_url,
            tier2_model=args.tier2_model,
            tier2_retry=args.retry,
            use_template_cache=args.use_template_cache,
        )
        print(result.to_json())
        if result.status == "executed_verified":
            return 0
        if result.status in {"executed_unverified", "escalate"}:
            return 1
        return 2

    if args.command == "capture":
        result = capture_screenshot(
            output_path=args.output,
            capture_method=args.capture_method,
            adb_serial=args.adb_serial,
            droidcast_url=args.droidcast_url,
            config_path=args.config_path,
            retries=args.capture_retries,
            retry_delay_ms=args.capture_retry_delay_ms,
        )
        print(result.to_json())
        return 0 if result.status == "success" else 2

    raise SystemExit("unsupported command")


if __name__ == "__main__":
    raise SystemExit(main())
