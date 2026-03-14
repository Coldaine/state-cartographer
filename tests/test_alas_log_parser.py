"""Tests for alas_log_parser.py — ALAS log parsing and analysis."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from alas_log_parser import LogParser, NavigationAnalyzer, SessionState, TaskAnalyzer

# ---------------------------------------------------------------------------
# Real log snippets extracted from vendor/AzurLaneAutoScript/log/
# ---------------------------------------------------------------------------

REAL_LOG_SNIPPET = [
    "2026-03-14 00:44:19.070 | INFO | [UI] page_main",
    "2026-03-14 00:44:19.072 | INFO | Goto page_reward",
    "2026-03-14 00:44:19.074 | INFO | <<< UI GOTO PAGE_REWARD >>>",
    "2026-03-14 00:44:19.083 | INFO | Page switch: page_main_white -> page_reward",
    "2026-03-14 00:44:19.085 | INFO | Click (  21,  232) @ MAIN_GOTO_REWARD_WHITE",
    "2026-03-14 00:44:20.339 | INFO | Page arrive: page_reward",
    "2026-03-14 00:44:20.370 | INFO | Click ( 461,  282) @ REWARD_GOTO_COMMISSION",
]

TASK_LIFECYCLE_SNIPPET = [
    "2026-03-14 00:43:55.910 | INFO | Scheduler: Start task `Commission`",
    "2026-03-14 00:44:29.714 | INFO | Delay task `Commission` to 2026-03-14 01:33:10 (success=False)",
    "2026-03-14 00:44:29.724 | INFO | Scheduler: End task `Commission`",
    "2026-03-14 00:44:29.742 | INFO | Scheduler: Start task `Research`",
]


class TestLogParser:
    def test_parses_structured_log_line(self):
        lines = ["2026-03-14 00:44:19.070 | INFO | [UI] page_main"]
        parsed = list(LogParser.parse(iter(lines)))
        assert len(parsed) == 1
        assert parsed[0].timestamp == datetime(2026, 3, 14, 0, 44, 19, 70000)
        assert parsed[0].level == "INFO"
        assert parsed[0].message == "[UI] page_main"

    def test_parses_warning_and_error_levels(self):
        lines = [
            "2026-03-14 00:44:00.100 | WARNING | Something fishy",
            "2026-03-14 00:44:00.200 | ERROR | GameStuckError: stuck",
        ]
        parsed = list(LogParser.parse(iter(lines)))
        assert parsed[0].level == "WARNING"
        assert parsed[1].level == "ERROR"

    def test_separator_lines_detected(self):
        lines = [
            "═" * 60,
            "2026-03-14 00:44:19.070 | INFO | test message",
        ]
        parsed = list(LogParser.parse(iter(lines)))
        assert parsed[0].is_separator is True
        assert parsed[1].is_separator is False

    def test_continuation_lines_attached(self):
        lines = [
            "2026-03-14 00:44:00.100 | ERROR | Traceback:",
            "  File foo.py, line 1",
            "  File bar.py, line 2",
            "2026-03-14 00:44:00.200 | INFO | Next log",
        ]
        parsed = list(LogParser.parse(iter(lines)))
        assert len(parsed) == 2
        assert len(parsed[0].continuation_lines) == 2
        assert "foo.py" in parsed[0].full_message()

    def test_empty_input(self):
        parsed = list(LogParser.parse(iter([])))
        assert parsed == []

    def test_malformed_line_becomes_standalone(self):
        lines = ["this is not a log line at all"]
        parsed = list(LogParser.parse(iter(lines)))
        assert len(parsed) == 1
        assert parsed[0].message == "this is not a log line at all"

    def test_parses_real_log_snippet(self):
        parsed = list(LogParser.parse(iter(REAL_LOG_SNIPPET)))
        assert len(parsed) == 7
        messages = [p.message for p in parsed]
        assert "[UI] page_main" in messages
        assert "Page switch: page_main_white -> page_reward" in messages
        assert "Page arrive: page_reward" in messages


class TestNavigationAnalyzer:
    def test_page_switch_extracted(self):
        lines = ["2026-03-14 00:44:19.083 | INFO | Page switch: page_main_white -> page_reward"]
        nav = NavigationAnalyzer()
        state = SessionState()
        for log in LogParser.parse(iter(lines)):
            nav.feed(log, state)
        assert len(nav.page_switches) == 1
        assert nav.page_switches[0]["from"] == "page_main_white"
        assert nav.page_switches[0]["to"] == "page_reward"

    def test_multiple_page_switches(self):
        lines = [
            "2026-03-14 00:44:30.825 | INFO | Page switch: page_commission -> page_main",
            "2026-03-14 00:44:33.121 | INFO | Page switch: page_main_white -> page_reshmenu",
            "2026-03-14 00:44:38.500 | INFO | Page switch: page_reshmenu -> page_research",
        ]
        nav = NavigationAnalyzer()
        state = SessionState()
        for log in LogParser.parse(iter(lines)):
            nav.feed(log, state)
        assert len(nav.page_switches) == 3
        assert nav.page_switches[2]["to"] == "page_research"

    def test_click_counting(self):
        lines = [
            "2026-03-14 00:44:19.085 | INFO | Click (  21,  232) @ MAIN_GOTO_REWARD_WHITE",
            "2026-03-14 00:44:20.370 | INFO | Click ( 461,  282) @ REWARD_GOTO_COMMISSION",
            "2026-03-14 00:44:21.992 | INFO | Click (  57,  265) @ COMMISSION_URGENT",
        ]
        nav = NavigationAnalyzer()
        state = SessionState()
        for log in LogParser.parse(iter(lines)):
            nav.feed(log, state)
        assert nav.click_count == 3

    def test_unknown_page_counting(self):
        lines = [
            "2026-03-14 00:43:57.160 | INFO | Unknown ui page",
            "2026-03-14 00:43:57.645 | INFO | Unknown ui page",
            "2026-03-14 00:43:57.917 | INFO | Unknown ui page",
            "2026-03-14 00:44:19.070 | INFO | [UI] page_main",
        ]
        nav = NavigationAnalyzer()
        state = SessionState()
        for log in LogParser.parse(iter(lines)):
            nav.feed(log, state)
        assert nav.unknown_pages == 3

    def test_real_log_snippet_full_pipeline(self):
        nav = NavigationAnalyzer()
        state = SessionState()
        for log in LogParser.parse(iter(REAL_LOG_SNIPPET)):
            nav.feed(log, state)
        assert len(nav.page_switches) == 1
        assert nav.page_switches[0]["from"] == "page_main_white"
        assert nav.page_switches[0]["to"] == "page_reward"
        assert nav.click_count == 2
        assert nav.unknown_pages == 0

    def test_ignores_non_navigation_lines(self):
        lines = [
            "2026-03-14 00:44:21.989 | INFO | Commission_switch set to urgent",
            "2026-03-14 00:44:24.549 | INFO | [COMMISSION_SCROLL_AREA] 0.01 (182.5-181.0)/(599-362)",
        ]
        nav = NavigationAnalyzer()
        state = SessionState()
        for log in LogParser.parse(iter(lines)):
            nav.feed(log, state)
        assert len(nav.page_switches) == 0
        assert nav.click_count == 0


class TestTaskAnalyzer:
    def test_task_start_and_end(self):
        tasks = TaskAnalyzer()
        state = SessionState()
        for log in LogParser.parse(iter(TASK_LIFECYCLE_SNIPPET)):
            tasks.feed(log, state)
        assert len(tasks.tasks) >= 1
        assert tasks.tasks[0].name == "Commission"

    def test_current_task_updated_in_session_state(self):
        lines = ["2026-03-14 00:43:55.910 | INFO | Scheduler: Start task `Commission`"]
        tasks = TaskAnalyzer()
        state = SessionState()
        for log in LogParser.parse(iter(lines)):
            tasks.feed(log, state)
        assert state.current_task == "Commission"


class TestLogParserWithRealFile:
    """Test against the real ALAS log file if it exists."""

    @pytest.fixture
    def real_log_path(self):
        p = Path(__file__).parent.parent / "vendor" / "AzurLaneAutoScript" / "log" / "2026-03-14_PatrickCustom.txt"
        if not p.exists():
            pytest.skip("Real ALAS log file not available")
        return p

    def test_parses_real_file_without_crash(self, real_log_path):
        nav = NavigationAnalyzer()
        state = SessionState()
        count = 0
        with open(real_log_path, encoding="utf-8", errors="replace") as f:
            for log in LogParser.parse(f):
                nav.feed(log, state)
                count += 1
        assert count > 100
        assert len(nav.page_switches) > 0
        assert nav.click_count > 0

    def test_real_file_pages_are_valid_alas_pages(self, real_log_path):
        nav = NavigationAnalyzer()
        state = SessionState()
        with open(real_log_path, encoding="utf-8", errors="replace") as f:
            for log in LogParser.parse(f):
                nav.feed(log, state)
        for sw in nav.page_switches:
            assert sw["from"].startswith("page_")
            assert sw["to"].startswith("page_")
