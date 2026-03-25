from __future__ import annotations

import json
import os
from pathlib import Path

from runtime.config.models import RuntimeConfig


def load_runtime_config(path: str | Path | None = None) -> RuntimeConfig:
    candidate = Path(path or "configs/memu.json")
    payload: dict[str, object] = {}
    if candidate.is_file():
        payload = json.loads(candidate.read_text(encoding="utf-8"))

    ports = payload.get("ports") if isinstance(payload.get("ports"), dict) else {}
    droidcast_url = os.getenv("SC_DROIDCAST_URL")
    if not droidcast_url and "droidcast" in ports:
        droidcast_url = f"http://127.0.0.1:{ports['droidcast']}"

    return RuntimeConfig(
        adb_serial=str(os.getenv("SC_ADB_SERIAL") or payload.get("adb_serial") or "127.0.0.1:21513"),
        objective_tag=str(payload.get("objective_tag") or "commission_collect"),
        scrcpy_executable=str(os.getenv("SC_SCRCPY_BIN") or "scrcpy"),
        scrcpy_max_fps=int(os.getenv("SC_SCRCPY_MAX_FPS") or 15),
        stream_fallback=str(os.getenv("SC_STREAM_FALLBACK") or payload.get("screenshot_method") or "droidcast"),
        droidcast_url=droidcast_url,
        artifact_root=Path(os.getenv("SC_RUNTIME_ARTIFACT_ROOT") or "data/runtime"),
        actor_base_url=str(os.getenv("SC_VLM_BASE_URL") or "http://localhost:18900/v1"),
        actor_model=str(os.getenv("SC_VLM_MODEL") or "local-vlm"),
        verifier_model=os.getenv("SC_VLM_VERIFY_MODEL"),
        extras=payload,
    )
