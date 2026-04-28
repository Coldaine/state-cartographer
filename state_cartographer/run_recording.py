"""Shared run-provenance helpers for production-ish script entrypoints."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import subprocess
from contextlib import suppress
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from state_cartographer.transport.action_log import start_session

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_RUNS_ROOT = _REPO_ROOT / "data" / "runs"
_DEFAULT_SUMMARY_ROOT = _REPO_ROOT / "docs" / "sessions" / "auto"


def repo_root() -> Path:
    return _REPO_ROOT


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _iso_now() -> str:
    return _now_utc().isoformat()


def _slugify(value: str) -> str:
    cleaned = []
    for char in value.lower():
        if char.isalnum():
            cleaned.append(char)
        else:
            cleaned.append("-")
    slug = "".join(cleaned).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "run"


def _runs_root() -> Path:
    override = os.getenv("SC_RUN_DATA_ROOT")
    return Path(override) if override else _DEFAULT_RUNS_ROOT


def _summary_root() -> Path:
    override = os.getenv("SC_RUN_SUMMARY_ROOT")
    return Path(override) if override else _DEFAULT_SUMMARY_ROOT


def _normalize_path(path: Path | str | None) -> str | None:
    if path is None:
        return None
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(_REPO_ROOT))
    except ValueError:
        return str(resolved)


def _path_exists(path: Path | str | None) -> bool:
    return path is not None and Path(path).exists()


def _relative_link(base_dir: Path, target: Path) -> str:
    try:
        relative = target.resolve().relative_to(_REPO_ROOT)
        return relative.as_posix()
    except ValueError:
        return os.path.relpath(target.resolve(), start=base_dir.resolve()).replace("\\", "/")


def _file_sha256(path: Path | str | None) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    if not candidate.exists() or not candidate.is_file():
        return None
    digest = hashlib.sha256()
    with candidate.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_git(args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=_REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def _git_dirty() -> bool | None:
    output = _run_git(["status", "--short"])
    if output is None:
        return None
    return bool(output)


@dataclass
class RunEvent:
    """One runtime event written to the per-run NDJSON stream."""

    kind: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_iso_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "kind": self.kind,
            "payload": self.payload,
        }


@dataclass
class RunManifest:
    """Tracked metadata for a single script invocation."""

    run_id: str
    lane: str
    command: list[str]
    cwd: str
    started_at: str
    status: str = "in_progress"
    finished_at: str | None = None
    exit_code: int | None = None
    branch: str | None = None
    commit: str | None = None
    git_dirty: bool | None = None
    config_path: str | None = None
    config_sha256: str | None = None
    serial: str | None = None
    model: str | None = None
    base_url: str | None = None
    input_paths: dict[str, str] = field(default_factory=dict)
    output_paths: dict[str, str] = field(default_factory=dict)
    summary_counts: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    manifest_path: str | None = None
    events_path: str | None = None
    summary_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunSummary:
    """Compact tracked summary derived from a finished manifest."""

    manifest: RunManifest

    def to_markdown(self) -> str:
        lines = [
            f"# Run Summary: {self.manifest.lane}",
            "",
            f"- Run ID: `{self.manifest.run_id}`",
            f"- Status: `{self.manifest.status}`",
            f"- Exit code: `{self.manifest.exit_code}`",
            f"- Started: `{self.manifest.started_at}`",
            f"- Finished: `{self.manifest.finished_at}`",
            f"- Command: `{' '.join(self.manifest.command)}`",
        ]
        if self.manifest.branch or self.manifest.commit:
            branch = self.manifest.branch or "unknown"
            commit = self.manifest.commit or "unknown"
            lines.append(f"- Git: `{branch}` @ `{commit}` dirty=`{self.manifest.git_dirty}`")
        if self.manifest.config_path:
            lines.append(f"- Config: `{self.manifest.config_path}`")
        if self.manifest.serial:
            lines.append(f"- Serial: `{self.manifest.serial}`")
        if self.manifest.model:
            lines.append(f"- Model: `{self.manifest.model}`")
        if self.manifest.base_url:
            lines.append(f"- Base URL: `{self.manifest.base_url}`")
        lines.append("")
        lines.append("## Outputs")
        if self.manifest.output_paths:
            for key, value in sorted(self.manifest.output_paths.items()):
                raw_path = _REPO_ROOT / value if not Path(value).is_absolute() else Path(value)
                if raw_path.exists():
                    link_target = _relative_link(_summary_root(), raw_path)
                    lines.append(f"- `{key}`: [{value}]({link_target})")
                else:
                    lines.append(f"- `{key}`: `{value}`")
        else:
            lines.append("- None")
        lines.append("")
        lines.append("## Counts")
        if self.manifest.summary_counts:
            for key, value in sorted(self.manifest.summary_counts.items()):
                lines.append(f"- `{key}`: `{value}`")
        else:
            lines.append("- None")
        if self.manifest.warnings:
            lines.append("")
            lines.append("## Warnings")
            for warning in self.manifest.warnings:
                lines.append(f"- {warning}")
        if self.manifest.notes:
            lines.append("")
            lines.append("## Notes")
            for note in self.manifest.notes:
                lines.append(f"- {note}")
        lines.append("")
        lines.append("## Files")
        for label in ("manifest_path", "events_path", "summary_path"):
            value = getattr(self.manifest, label)
            if value:
                lines.append(f"- `{label}`: `{value}`")
        return "\n".join(lines) + "\n"


class RunRecorder:
    """Manage manifest, event stream, and promoted summary generation."""

    def __init__(
        self,
        lane: str,
        *,
        command: list[str] | None = None,
        cwd: Path | str | None = None,
        write_summary: bool = True,
        summary_root: Path | str | None = None,
    ):
        self.lane = lane
        self.command = command or []
        self.cwd = Path(cwd) if cwd else Path.cwd()
        self.write_summary = write_summary
        self.summary_root = Path(summary_root) if summary_root else _summary_root()
        self.run_id: str | None = None
        self.run_root: Path | None = None
        self.artifacts_dir: Path | None = None
        self.manifest_path: Path | None = None
        self.events_path: Path | None = None
        self.summary_path: Path | None = None
        self.manifest: RunManifest | None = None

    @staticmethod
    def make_run_id(lane: str) -> str:
        stamp = _now_utc().strftime("%Y%m%dT%H%M%SZ")
        token = secrets.token_hex(4)
        return f"{stamp}-{_slugify(lane)}-{token}"

    def start(
        self,
        *,
        run_id: str | None = None,
        config_path: Path | str | None = None,
        serial: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        input_paths: dict[str, Path | str] | None = None,
        notes: list[str] | None = None,
    ) -> str:
        if self.manifest is not None:
            raise RuntimeError("run recorder already started")

        started_at = _now_utc()
        self.run_id = run_id or self.make_run_id(self.lane)
        self.run_root = _runs_root() / self.run_id
        self.artifacts_dir = self.run_root / _slugify(self.lane)
        self.manifest_path = self.run_root / "manifest.json"
        self.events_path = self.run_root / "events.ndjson"
        if self.write_summary:
            summary_name = f"{started_at.strftime('%Y-%m-%d')}_{_slugify(self.lane)}_{self.run_id}.md"
            self.summary_path = self.summary_root / summary_name

        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        if self.summary_path is not None:
            self.summary_path.parent.mkdir(parents=True, exist_ok=True)

        with suppress(Exception):
            start_session(self.run_id)

        manifest = RunManifest(
            run_id=self.run_id,
            lane=self.lane,
            command=self.command,
            cwd=_normalize_path(self.cwd) or str(self.cwd),
            started_at=started_at.isoformat(),
            branch=_run_git(["rev-parse", "--abbrev-ref", "HEAD"]),
            commit=_run_git(["rev-parse", "HEAD"]),
            git_dirty=_git_dirty(),
            config_path=_normalize_path(config_path),
            config_sha256=_file_sha256(config_path),
            serial=serial,
            model=model,
            base_url=base_url,
            input_paths={k: _normalize_path(v) or str(v) for k, v in (input_paths or {}).items()},
            output_paths={"artifacts_dir": _normalize_path(self.artifacts_dir) or str(self.artifacts_dir)},
            notes=list(notes or []),
            manifest_path=_normalize_path(self.manifest_path),
            events_path=_normalize_path(self.events_path),
            summary_path=_normalize_path(self.summary_path),
        )
        self.manifest = manifest
        self._write_manifest()
        self.event("run_started", lane=self.lane, artifacts_dir=manifest.output_paths["artifacts_dir"])
        return self.run_id

    def artifact_path(self, *parts: str) -> Path:
        if self.artifacts_dir is None:
            raise RuntimeError("run recorder not started")
        path = self.artifacts_dir.joinpath(*parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def event(self, kind: str, **payload: Any) -> None:
        if self.events_path is None:
            raise RuntimeError("run recorder not started")
        entry = RunEvent(kind=kind, payload=payload)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.to_dict(), sort_keys=True) + "\n")

    def finish(
        self,
        *,
        exit_code: int,
        status: str | None = None,
        output_paths: dict[str, Path | str] | None = None,
        summary_counts: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
        notes: list[str] | None = None,
    ) -> RunManifest:
        if self.manifest is None:
            raise RuntimeError("run recorder not started")

        self.manifest.exit_code = exit_code
        self.manifest.status = status or ("succeeded" if exit_code == 0 else "failed")
        self.manifest.finished_at = _iso_now()
        if output_paths:
            self.manifest.output_paths.update({k: _normalize_path(v) or str(v) for k, v in output_paths.items()})
        if summary_counts:
            self.manifest.summary_counts.update(summary_counts)
        if warnings:
            self.manifest.warnings.extend(warnings)
        if notes:
            self.manifest.notes.extend(notes)

        self.event(
            "run_finished",
            exit_code=exit_code,
            status=self.manifest.status,
            summary_counts=self.manifest.summary_counts,
            warnings=self.manifest.warnings,
        )
        self._write_manifest()
        self._write_summary()
        return self.manifest

    def _write_manifest(self) -> None:
        if self.manifest is None or self.manifest_path is None:
            raise RuntimeError("run recorder not started")
        self.manifest_path.write_text(
            json.dumps(self.manifest.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def _write_summary(self) -> None:
        if not self.write_summary or self.manifest is None or self.summary_path is None:
            return
        summary = RunSummary(self.manifest)
        self.summary_path.write_text(summary.to_markdown(), encoding="utf-8")
