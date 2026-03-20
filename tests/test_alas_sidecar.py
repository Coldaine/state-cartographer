"""Tests for alas_sidecar.py — labeled screenshot corpus builder."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from alas_sidecar import (
    _make_record,
    follow_file,
    get_latest_log_file,
    run_sidecar,
)

# ---------------------------------------------------------------------------
# _make_record
# ---------------------------------------------------------------------------


def test_make_record_produces_valid_jsonl(tmp_path: Path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    png = corpus / "000001.png"
    png.write_bytes(b"fake")

    rec = _make_record(
        path=png,
        alas_page="page_main",
        alas_task="Commission",
        trigger="PageSwitch",
        log_line_no=42,
        corpus_dir=corpus,
    )

    assert rec["alas_page"] == "page_main"
    assert rec["alas_task"] == "Commission"
    assert rec["trigger"] == "PageSwitch"
    assert rec["log_line"] == 42
    assert "ts" in rec
    # Must be JSON-serializable
    json.loads(json.dumps(rec))


# ---------------------------------------------------------------------------
# get_latest_log_file
# ---------------------------------------------------------------------------


def test_get_latest_log_file_picks_newest(tmp_path: Path):
    old = tmp_path / "2026-03-18_PatrickCustom.txt"
    new = tmp_path / "2026-03-19_PatrickCustom.txt"
    old.write_text("old", encoding="utf-8")
    time.sleep(0.05)
    new.write_text("new", encoding="utf-8")

    result = get_latest_log_file(tmp_path)
    assert result == new


def test_get_latest_log_file_raises_on_empty_dir(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        get_latest_log_file(tmp_path)


def test_get_latest_log_file_raises_on_missing_dir():
    with pytest.raises(FileNotFoundError):
        get_latest_log_file(Path("/nonexistent/dir"))


# ---------------------------------------------------------------------------
# follow_file
# ---------------------------------------------------------------------------


def test_follow_file_yields_new_lines(tmp_path: Path):
    log = tmp_path / "test.log"
    log.write_text("", encoding="utf-8")

    lines_read: list[str] = []
    stop = threading.Event()

    def reader():
        for line in follow_file(log):
            lines_read.append(line.strip())
            if len(lines_read) >= 2 or stop.is_set():
                break

    t = threading.Thread(target=reader, daemon=True)
    t.start()

    # Give the reader time to seek to EOF
    time.sleep(0.3)

    with open(log, "a", encoding="utf-8") as f:
        f.write("line_one\n")
        f.flush()
        time.sleep(0.3)
        f.write("line_two\n")
        f.flush()

    t.join(timeout=5)
    stop.set()
    assert lines_read == ["line_one", "line_two"]


# ---------------------------------------------------------------------------
# run_sidecar (integration — with mocked screenshot capture)
# ---------------------------------------------------------------------------


def test_run_sidecar_captures_on_page_switch(tmp_path: Path):
    """Verify end-to-end: log line -> page tracking -> capture -> JSONL record."""
    corpus = tmp_path / "corpus"
    log_file = tmp_path / "test.log"
    # Pre-write the log lines so the sidecar finds them immediately
    log_file.write_text(
        "2026-03-20 14:00:00.000 | INFO | Page switch: page_unknown -> page_main\n"
        "2026-03-20 14:00:05.000 | INFO | Page switch: page_main -> page_commission\n",
        encoding="utf-8",
    )

    # Patch follow_file to read from start instead of tailing (avoids infinite wait)
    def _read_all_lines(path: Path):
        with open(path, encoding="utf-8") as f:
            yield from f

    with (
        patch("alas_sidecar.capture_screenshot") as mock_cap,
        patch("alas_sidecar.follow_file", side_effect=_read_all_lines),
    ):
        mock_cap.side_effect = lambda path, serial: (
            (
                path.parent.mkdir(parents=True, exist_ok=True),
                path.write_bytes(b"fake_png"),
            )[-1]
            or True
        )

        run_sidecar(
            serial="127.0.0.1:21513",
            interval=60,  # long interval so only page-switch captures fire
            corpus_dir=corpus,
            log_file=log_file,
            max_captures=2,
        )

    # Check index
    index = corpus / "index.jsonl"
    assert index.exists()
    records = [json.loads(line) for line in index.read_text(encoding="utf-8").strip().splitlines()]
    assert len(records) >= 2
    pages = [r["alas_page"] for r in records]
    assert "page_main" in pages
    assert "page_commission" in pages

    # All records should have required fields
    for rec in records:
        assert "ts" in rec
        assert "path" in rec
        assert "alas_page" in rec
        assert "trigger" in rec
