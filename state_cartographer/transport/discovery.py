"""Tool bootstrap and discovery for the transport layer.

Discovers: adb, MaaMCP/MaaFramework, scrcpy, adbfriend.
Records exact working baseline in artifacts.
Does NOT vendor third-party code.
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
from pathlib import Path

from state_cartographer.transport.config import TransportConfig, artifacts_dir
from state_cartographer.transport.models import BootstrapManifest, ToolEntry

log = logging.getLogger(__name__)

# Well-known search locations on Windows
_MEMU_INSTALL_DIRS = [
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Microvirt" / "MEmu",
    Path(r"D:\Program Files\Microvirt\MEmu"),
    Path(r"C:\Program Files\Microvirt\MEmu"),
]

_SCRCPY_SEARCH = [
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "scrcpy",
    Path(r"C:\scrcpy"),
]


def _which(name: str) -> str | None:
    return shutil.which(name)


def _run_version(exe: str, args: list[str] | None = None) -> str | None:
    cmd = [exe] + (args or ["--version"])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        out = (r.stdout or "").strip() or (r.stderr or "").strip()
        return out.split("\n")[0] if out else None
    except Exception:
        return None


def discover_adb(cfg: TransportConfig) -> ToolEntry:
    """Find adb — check PATH, then MEmu install dirs."""
    # PATH first
    found = _which("adb")
    if found:
        ver = _run_version(found)
        return ToolEntry(name="adb", found=True, path=found, version=ver, source="PATH")

    # MEmu bundled adb
    for d in _MEMU_INSTALL_DIRS:
        candidate = d / "adb.exe"
        if candidate.exists():
            ver = _run_version(str(candidate))
            return ToolEntry(name="adb", found=True, path=str(candidate), version=ver, source="memu_install")

    return ToolEntry(name="adb", found=False, error="adb not found in PATH or known MEmu install directories")


def discover_scrcpy(cfg: TransportConfig) -> ToolEntry:
    """Find scrcpy binary — check PATH then well-known dirs."""
    found = _which("scrcpy")
    if found:
        ver = _run_version(found)
        return ToolEntry(name="scrcpy", found=True, path=found, version=ver, source="PATH")

    for d in _SCRCPY_SEARCH:
        candidate = d / ("scrcpy.exe" if platform.system() == "Windows" else "scrcpy")
        if candidate.exists():
            ver = _run_version(str(candidate))
            return ToolEntry(name="scrcpy", found=True, path=str(candidate), version=ver, source="known_dir")

    return ToolEntry(name="scrcpy", found=False, error="scrcpy not found in PATH or known directories")


def discover_maamcp() -> ToolEntry:
    """Check if MaaFramework Python bindings are importable."""
    try:
        import importlib

        maafw = importlib.import_module("maa")
        ver = getattr(maafw, "__version__", "unknown")
        return ToolEntry(name="maamcp", found=True, version=str(ver), source="python_import")
    except ImportError:
        pass

    # Check for maa CLI tool
    found = _which("maa")
    if found:
        ver = _run_version(found, ["version"])
        return ToolEntry(name="maamcp", found=True, path=found, version=ver, source="PATH_cli")

    return ToolEntry(
        name="maamcp",
        found=False,
        error="MaaFramework not found. Install via: pip install maafw  (or place maa CLI on PATH)",
    )


def discover_adbfriend() -> ToolEntry:
    """Find adbfriend — optional, separate utility."""
    found = _which("adbfriend")
    if found:
        ver = _run_version(found)
        return ToolEntry(name="adbfriend", found=True, path=found, version=ver, source="PATH")
    return ToolEntry(name="adbfriend", found=False, error="adbfriend not found on PATH (optional)")


def bootstrap(cfg: TransportConfig) -> BootstrapManifest:
    """Run full tool discovery and produce a bootstrap manifest.

    Required tools: adb, maamcp
    Optional tools: scrcpy, adbfriend
    """
    tools: list[ToolEntry] = []
    errors: list[str] = []
    missing: list[str] = []

    adb = discover_adb(cfg)
    tools.append(adb)
    if not adb.found:
        missing.append("adb")
        errors.append(adb.error or "adb not found")

    maa = discover_maamcp()
    tools.append(maa)
    if not maa.found:
        missing.append("maamcp")
        errors.append(maa.error or "MaaMCP not found")

    scrcpy = discover_scrcpy(cfg)
    tools.append(scrcpy)

    adbfriend = discover_adbfriend()
    tools.append(adbfriend)

    manifest = BootstrapManifest(
        tools=tools,
        all_required_found=len(missing) == 0,
        missing=missing,
        errors=errors,
    )

    # Persist to artifacts
    out = artifacts_dir() / "bootstrap-manifest.json"
    out.write_text(manifest.to_json(), encoding="utf-8")
    log.info("Bootstrap manifest written to %s", out)

    return manifest
