"""Transport-layer action trace logger.

Logs every transport action to data/logs/{date}_{session_id}.log
as structured single-line key=value records.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_logger: logging.Logger | None = None
_session_id: str | None = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _log_dir() -> Path:
    d = _repo_root() / "data" / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


class _IsoFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ts_ns = time.time_ns()
        ts_s = ts_ns // 1_000_000_000
        ts_ns_rem = ts_ns % 1_000_000_000
        dt = datetime.fromtimestamp(ts_s, tz=UTC)
        iso = dt.strftime("%Y-%m-%dT%H:%M:%S") + f".{ts_ns_rem // 1_000_000:03d}Z"
        record.iso = iso
        return super().format(record)


def _configure_logger(session_id: str) -> logging.Logger:
    global _logger, _session_id

    logger = logging.getLogger("state_cartographer.transport.trace")
    logger.handlers.clear()

    logger.setLevel(logging.DEBUG)

    log_dir = _log_dir()
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    file_path = log_dir / f"{date_str}_{session_id}.log"

    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = _IsoFormatter("%(iso)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    _logger = logger
    _session_id = session_id
    return logger


def get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        ts_ns = time.time_ns()
        ts_s = ts_ns // 1_000_000_000
        default_session = f"default_{ts_s}"
        _configure_logger(default_session)
    return _logger


def start_session(session_id: str) -> None:
    _configure_logger(session_id)


def action(
    action_type: str,
    serial: str,
    control: str,
    params: dict[str, Any],
    result: str,
    duration_ms: float = 0.0,
    error: str | None = None,
) -> None:
    global _session_id

    if _session_id is None:
        ts_ns = time.time_ns()
        ts_s = ts_ns // 1_000_000_000
        auto_session = f"auto_{ts_s}"
        start_session(auto_session)

    parts = [
        f"action={action_type}",
        f"serial={serial}",
        f"control={control}",
    ]

    for k, v in params.items():
        parts.append(f"{k}={v}")

    parts.append(f"result={result}")
    parts.append(f"duration_ms={duration_ms:.2f}")

    if error is not None:
        parts.append(f"error={error}")

    message = " ".join(parts)

    logger = get_logger()
    logger.info(message)
