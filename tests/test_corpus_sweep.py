"""Tests for scripts/corpus_sweep.py.

Tests run offline — no VLM server, no emulator, no corpus required.
They verify parsing, merging, and extraction logic against synthetic fixtures.
"""

from __future__ import annotations

import json
import sys
import textwrap
from datetime import datetime
from pathlib import Path

# Put scripts/ on the path so corpus_sweep can be imported directly.
# This must happen before the module-level import below.
_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import corpus_sweep as cs  # noqa: E402

# ---------------------------------------------------------------------------
# label derivation
# ---------------------------------------------------------------------------


class TestDeriveCandidateLabels:
    def test_fallback_when_file_missing(self, tmp_path):
        labels = cs.derive_candidate_labels(tmp_path / "nonexistent.py")
        assert "page_main" in labels
        assert "page_commission" in labels
        assert len(labels) == 43

    def test_parse_live_page_file(self):
        labels = cs.derive_candidate_labels()
        assert "page_main" in labels
        assert all(label.startswith("page_") for label in labels)
        assert len(labels) >= 40

    def test_custom_page_file(self, tmp_path):
        fake = tmp_path / "page.py"
        fake.write_text(
            "page_alpha = Page()\npage_beta = Page()\nNOT_A_PAGE = Page()\n",
            encoding="utf-8",
        )
        labels = cs.derive_candidate_labels(fake)
        assert labels == ["page_alpha", "page_beta"]


# ---------------------------------------------------------------------------
# frame timestamp parsing
# ---------------------------------------------------------------------------


class TestFrameTimestamp:
    def test_valid_filename(self):
        ts = cs.frame_timestamp(Path("20260320_002241_384.png"))
        assert ts is not None
        assert ts.year == 2026
        assert ts.month == 3
        assert ts.day == 20
        assert ts.hour == 0
        assert ts.minute == 22
        assert ts.second == 41

    def test_invalid_filename_returns_none(self):
        assert cs.frame_timestamp(Path("01_page_main.png")) is None
        assert cs.frame_timestamp(Path("random.png")) is None
        assert cs.frame_timestamp(Path("")) is None


# ---------------------------------------------------------------------------
# ALAS log parser
# ---------------------------------------------------------------------------

LOG_SAMPLE = textwrap.dedent("""\
    2026-03-25 12:46:12.873 | INFO | <<< Commission >>>
    2026-03-25 12:46:13.100 | INFO | UI get to page_main
    2026-03-25 12:46:14.200 | INFO | Click GOTO_COMMISSION at (792, 42)
    2026-03-25 12:46:15.300 | INFO | UI get to page_commission
    2026-03-25 12:46:16.000 | INFO | Page: page_commission
    2026-03-25 12:46:17.000 | DEBUG | Some other debug line
    2026-03-25 12:46:18.000 | INFO | page_reward appear
""")


class TestALASLogParser:
    def test_parse_page_arrive(self, tmp_path):
        log = tmp_path / "log.txt"
        log.write_text(LOG_SAMPLE, encoding="utf-8")
        events = cs.parse_alas_log(log)
        arrive = [e for e in events if e.event_type == "page_arrive"]
        assert len(arrive) == 2
        assert arrive[0].page == "page_main"
        assert arrive[1].page == "page_commission"

    def test_parse_tap(self, tmp_path):
        log = tmp_path / "log.txt"
        log.write_text(LOG_SAMPLE, encoding="utf-8")
        events = cs.parse_alas_log(log)
        taps = [e for e in events if e.event_type == "tap"]
        assert len(taps) == 1
        assert taps[0].button == "GOTO_COMMISSION"
        assert taps[0].x == 792
        assert taps[0].y == 42

    def test_task_context_propagated(self, tmp_path):
        log = tmp_path / "log.txt"
        log.write_text(LOG_SAMPLE, encoding="utf-8")
        events = cs.parse_alas_log(log)
        for e in events:
            assert e.task == "Commission"

    def test_page_label_event(self, tmp_path):
        log = tmp_path / "log.txt"
        log.write_text(LOG_SAMPLE, encoding="utf-8")
        events = cs.parse_alas_log(log)
        page_label_events = [e for e in events if e.event_type == "page_label"]
        assert any(e.page == "page_commission" for e in page_label_events)

    def test_page_appear_event(self, tmp_path):
        log = tmp_path / "log.txt"
        log.write_text(LOG_SAMPLE, encoding="utf-8")
        events = cs.parse_alas_log(log)
        appear_events = [e for e in events if e.event_type == "page_appear"]
        assert any(e.page == "page_reward" for e in appear_events)

    def test_gui_log_produces_no_events(self, tmp_path):
        # GUI logs only contain launcher config lines — should produce nothing useful
        gui_log = tmp_path / "2026-03-25_gui.txt"
        gui_log.write_text(
            "2026-03-25 12:46:12.873 | INFO | <<< LAUNCHER CONFIG >>>\n"
            "2026-03-25 12:46:12.874 | INFO | [Host] 0.0.0.0\n",
            encoding="utf-8",
        )
        events = cs.parse_alas_log(gui_log)
        assert events == []

    def test_empty_log(self, tmp_path):
        log = tmp_path / "empty.txt"
        log.write_text("", encoding="utf-8")
        assert cs.parse_alas_log(log) == []

    def test_to_dict_round_trips(self, tmp_path):
        log = tmp_path / "log.txt"
        log.write_text(LOG_SAMPLE, encoding="utf-8")
        events = cs.parse_alas_log(log)
        for e in events:
            d = e.to_dict()
            assert "timestamp" in d
            assert "event_type" in d
            # Should be JSON-serialisable
            json.dumps(d)


# ---------------------------------------------------------------------------
# Timeline merger (_nearest_event)
# ---------------------------------------------------------------------------


class TestNearestEvent:
    def _make_event(self, ts_str: str, page: str) -> cs.ALASLogEvent:
        return cs.ALASLogEvent(
            timestamp=datetime.fromisoformat(ts_str),
            level="INFO",
            raw_message="",
            event_type="page_arrive",
            page=page,
        )

    def test_finds_nearest(self):
        events = [
            self._make_event("2026-03-20 00:22:40.000", "page_main"),
            self._make_event("2026-03-20 00:22:45.000", "page_commission"),
        ]
        query = datetime.fromisoformat("2026-03-20 00:22:41.000")
        nearest = cs._nearest_event(query, events, window_s=2.0)
        assert nearest is not None
        assert nearest.page == "page_main"

    def test_no_match_outside_window(self):
        events = [
            self._make_event("2026-03-20 00:22:30.000", "page_main"),
        ]
        query = datetime.fromisoformat("2026-03-20 00:22:41.000")
        nearest = cs._nearest_event(query, events, window_s=2.0)
        assert nearest is None

    def test_empty_events(self):
        query = datetime.fromisoformat("2026-03-20 00:22:41.000")
        assert cs._nearest_event(query, [], window_s=2.0) is None


# ---------------------------------------------------------------------------
# Pass 2 — timeline merge (end-to-end with tmp files)
# ---------------------------------------------------------------------------


class TestPass2:
    def test_merge_with_no_alas_logs(self, tmp_path):
        pass1_file = tmp_path / "pass1.jsonl"
        pass1_file.write_text(
            json.dumps(
                {
                    "file": "20260320_002241_384.png",
                    "timestamp": "2026-03-20T00:22:41",
                    "label": "page_main",
                    "confidence": 0.9,
                    "pass": 1,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        out = tmp_path / "pass2.jsonl"
        results = cs.run_pass2(pass1_file=pass1_file, out_file=out, alas_log_dir=tmp_path / "nologs")
        assert len(results) == 1
        assert results[0]["alas_page"] is None
        assert results[0]["label"] == "page_main"
        assert out.exists()

    def test_merge_matches_event(self, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        log = log_dir / "2026-03-20_alas.txt"
        log.write_text(
            "2026-03-20 00:22:41.500 | INFO | UI get to page_main\n",
            encoding="utf-8",
        )
        pass1_file = tmp_path / "pass1.jsonl"
        pass1_file.write_text(
            json.dumps(
                {
                    "file": "20260320_002241_384.png",
                    "timestamp": "2026-03-20T00:22:41",
                    "label": "page_commission",
                    "confidence": 0.9,
                    "pass": 1,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        out = tmp_path / "pass2.jsonl"
        results = cs.run_pass2(pass1_file=pass1_file, out_file=out, alas_log_dir=log_dir, window_s=2.0)
        assert results[0]["alas_page"] == "page_main"


# ---------------------------------------------------------------------------
# Pass 4 — triple extraction
# ---------------------------------------------------------------------------


class TestPass4:
    def _write_merged(self, tmp_path: Path, rows: list[dict]) -> Path:
        f = tmp_path / "pass2.jsonl"
        f.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        return f

    def test_extracts_transition(self, tmp_path):
        rows = [
            {"file": "a.png", "timestamp": "2026-03-20T00:22:40", "label": "page_main", "confidence": 0.9},
            {"file": "b.png", "timestamp": "2026-03-20T00:22:42", "label": "page_commission", "confidence": 0.85},
        ]
        merged = self._write_merged(tmp_path, rows)
        out = tmp_path / "triples.jsonl"
        triples = cs.run_pass4(pass3_file=tmp_path / "no_pass3.jsonl", pass2_file=merged, out_file=out)
        assert len(triples) == 1
        assert triples[0]["source_page"] == "page_main"
        assert triples[0]["target_page"] == "page_commission"

    def test_no_transition_same_label(self, tmp_path):
        rows = [
            {"file": "a.png", "timestamp": "2026-03-20T00:22:40", "label": "page_main", "confidence": 0.9},
            {"file": "b.png", "timestamp": "2026-03-20T00:22:42", "label": "page_main", "confidence": 0.88},
        ]
        merged = self._write_merged(tmp_path, rows)
        out = tmp_path / "triples.jsonl"
        triples = cs.run_pass4(pass3_file=tmp_path / "no_pass3.jsonl", pass2_file=merged, out_file=out)
        assert len(triples) == 0

    def test_low_confidence_breaks_chain(self, tmp_path):
        rows = [
            {"file": "a.png", "timestamp": "2026-03-20T00:22:40", "label": "page_main", "confidence": 0.9},
            {"file": "b.png", "timestamp": "2026-03-20T00:22:41", "label": "page_commission", "confidence": 0.3},
            {"file": "c.png", "timestamp": "2026-03-20T00:22:42", "label": "page_reward", "confidence": 0.9},
        ]
        merged = self._write_merged(tmp_path, rows)
        out = tmp_path / "triples.jsonl"
        # Low confidence on b breaks the chain — no triple from a→b or b→c
        triples = cs.run_pass4(
            pass3_file=tmp_path / "no_pass3.jsonl",
            pass2_file=merged,
            out_file=out,
            min_confidence=0.6,
        )
        assert len(triples) == 0

    def test_uses_resolved_label_when_available(self, tmp_path):
        rows = [
            {
                "file": "a.png",
                "timestamp": "2026-03-20T00:22:40",
                "label": "page_main",
                "resolved_label": "page_main",
                "confidence": 0.9,
            },
            {
                "file": "b.png",
                "timestamp": "2026-03-20T00:22:42",
                "label": "page_unknown",
                "resolved_label": "page_commission",
                "confidence": 0.85,
            },
        ]
        merged = self._write_merged(tmp_path, rows)
        out = tmp_path / "triples.jsonl"
        triples = cs.run_pass4(pass3_file=tmp_path / "no_pass3.jsonl", pass2_file=merged, out_file=out)
        assert len(triples) == 1
        assert triples[0]["target_page"] == "page_commission"

    def test_missing_input_returns_empty(self, tmp_path):
        out = tmp_path / "triples.jsonl"
        triples = cs.run_pass4(
            pass3_file=tmp_path / "no_pass3.jsonl",
            pass2_file=tmp_path / "no_pass2.jsonl",
            out_file=out,
        )
        assert triples == []
