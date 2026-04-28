"""Unit tests for scripts/census_extract.py."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.census_extract import (
    CensusDB,
    _discover_capture_dir,
    _parse_json_response,
    build_parser,
    extract_grid_page,
    extract_ship_detail,
    extract_ship_gear,
    main,
    run_extraction,
)

# ---------------------------------------------------------------------------
# _parse_json_response
# ---------------------------------------------------------------------------


def test_parse_json_response_plain():
    text = '{"ships": [{"name": "Enterprise"}]}'
    result = _parse_json_response(text)
    assert result == {"ships": [{"name": "Enterprise"}]}


def test_parse_json_response_code_fence():
    text = '```json\n{"ships": [{"name": "Laffey", "level": 100}]}\n```'
    result = _parse_json_response(text)
    assert result == {"ships": [{"name": "Laffey", "level": 100}]}


def test_parse_json_response_plain_fence_no_lang():
    # Fences without a language tag should also be stripped.
    text = '```\n{"key": "value"}\n```'
    result = _parse_json_response(text)
    assert result == {"key": "value"}


# ---------------------------------------------------------------------------
# CensusDB — schema creation
# ---------------------------------------------------------------------------


def test_census_db_schema_creation(tmp_path):
    db_file = tmp_path / "test.db"
    db = CensusDB(db_file)

    conn = sqlite3.connect(str(db_file))
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    db.close()

    assert "census_runs" in tables
    assert "ships" in tables
    assert "equipment" in tables


# ---------------------------------------------------------------------------
# CensusDB — start_run / complete_run
# ---------------------------------------------------------------------------


def test_census_db_start_and_complete_run(tmp_path):
    db = CensusDB(tmp_path / "test.db")

    run_id = db.start_run(
        capture_dir="data/census/2026-04-04_120000",
        grid_pages=3,
        ships_processed=0,
    )
    assert isinstance(run_id, int)
    assert run_id >= 1

    # Status should be 'in_progress' after start.
    row = db.conn.execute("SELECT status, grid_pages FROM census_runs WHERE id = ?", (run_id,)).fetchone()
    assert row[0] == "in_progress"
    assert row[1] == 3

    db.complete_run(run_id)

    row = db.conn.execute("SELECT status FROM census_runs WHERE id = ?", (run_id,)).fetchone()
    assert row[0] == "complete"

    db.close()


# ---------------------------------------------------------------------------
# CensusDB — upsert_ship dedup
# ---------------------------------------------------------------------------


def test_census_db_upsert_ship_dedup(tmp_path):
    db = CensusDB(tmp_path / "test.db")
    run_id = db.start_run("data/census/run1", grid_pages=1, ships_processed=0)

    ship = {"slot_index": 0, "name": "Enterprise", "level": 120, "rarity": "Super Rare", "ship_class": "CV"}
    db.upsert_ship(run_id, ship)
    db.upsert_ship(run_id, ship)  # second insert — should update, not duplicate

    count = db.conn.execute(
        "SELECT COUNT(*) FROM ships WHERE census_run_id = ? AND slot_index = 0",
        (run_id,),
    ).fetchone()[0]
    assert count == 1

    db.close()


# ---------------------------------------------------------------------------
# CensusDB — upsert_ship COALESCE merge
# ---------------------------------------------------------------------------


def test_census_db_upsert_ship_coalesce(tmp_path):
    db = CensusDB(tmp_path / "test.db")
    run_id = db.start_run("data/census/run1", grid_pages=1, ships_processed=0)

    # First insert: grid page data — name + rarity only, no affinity/limit_break.
    db.upsert_ship(run_id, {"slot_index": 0, "name": "Laffey", "rarity": "Elite", "ship_class": "DD"})

    # Second insert: detail page data — enriches with affinity and limit_break.
    db.upsert_ship(
        run_id,
        {
            "slot_index": 0,
            "name": "Laffey",
            "level": 125,
            "affinity": "Love",
            "limit_break": 3,
        },
    )

    row = db.conn.execute(
        "SELECT rarity, ship_class, level, affinity, limit_break, slot_index "
        "FROM ships WHERE census_run_id = ? AND slot_index = 0",
        (run_id,),
    ).fetchone()

    # Rarity and ship_class from first insert must be preserved (COALESCE).
    assert row[0] == "Elite"
    assert row[1] == "DD"
    # Level, affinity, limit_break from second insert must be present.
    assert row[2] == 125
    assert row[3] == "Love"
    assert row[4] == 3
    assert row[5] == 0

    db.close()


def test_census_db_duplicate_ship_names_use_slot_identity(tmp_path):
    db = CensusDB(tmp_path / "test.db")
    run_id = db.start_run("data/census/run1", grid_pages=1, ships_processed=0)

    db.upsert_ship(run_id, {"slot_index": 0, "name": "Laffey", "rarity": "Elite", "ship_class": "DD"})
    db.upsert_ship(run_id, {"slot_index": 1, "name": "Laffey", "rarity": "Elite", "ship_class": "DD"})

    rows = db.conn.execute(
        "SELECT slot_index, name FROM ships WHERE census_run_id = ? ORDER BY slot_index",
        (run_id,),
    ).fetchall()
    assert rows == [(0, "Laffey"), (1, "Laffey")]

    db.close()


# ---------------------------------------------------------------------------
# CensusDB — add_equipment
# ---------------------------------------------------------------------------


def test_census_db_add_equipment(tmp_path):
    db = CensusDB(tmp_path / "test.db")
    run_id = db.start_run("data/census/run1", grid_pages=1, ships_processed=0)
    ship_id = db.upsert_ship(run_id, {"slot_index": 0, "name": "Yuudachi", "rarity": "Elite", "ship_class": "DD"})

    equip = {"slot": 1, "name": "Twin 127mm", "level": 10, "rarity": "Gold"}
    db.add_equipment(ship_id, equip)

    row = db.conn.execute(
        "SELECT slot, name, level, rarity FROM equipment WHERE ship_id = ?",
        (ship_id,),
    ).fetchone()

    assert row[0] == "1"
    assert row[1] == "Twin 127mm"
    assert row[2] == 10
    assert row[3] == "Gold"

    db.close()


# ---------------------------------------------------------------------------
# _discover_capture_dir
# ---------------------------------------------------------------------------


def test_discover_capture_dir(tmp_path):
    grid_dir = tmp_path / "grid"
    ships_dir = tmp_path / "ships"
    grid_dir.mkdir()
    ships_dir.mkdir()

    (grid_dir / "page_000.png").write_bytes(b"fake")
    (grid_dir / "page_001.png").write_bytes(b"fake")
    (ships_dir / "000_detail.png").write_bytes(b"fake")
    (ships_dir / "000_gear.png").write_bytes(b"fake")
    (ships_dir / "001_detail.png").write_bytes(b"fake")

    grid_pages, ship_files = _discover_capture_dir(tmp_path)

    assert len(grid_pages) == 2
    assert grid_pages[0].name == "page_000.png"
    assert grid_pages[1].name == "page_001.png"

    assert "000" in ship_files
    assert "001" in ship_files
    assert ship_files["000"]["detail"].name == "000_detail.png"
    assert ship_files["000"]["gear"].name == "000_gear.png"
    assert "detail" in ship_files["001"]
    assert "gear" not in ship_files["001"]


def test_discover_capture_dir_empty(tmp_path):
    grid_pages, ship_files = _discover_capture_dir(tmp_path)
    assert grid_pages == []
    assert ship_files == {}


# ---------------------------------------------------------------------------
# extract_grid_page — mocked VLMClient
# ---------------------------------------------------------------------------


def test_extract_grid_page_mock(tmp_path):
    image_path = tmp_path / "page_000.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)  # minimal fake PNG

    mock_client = MagicMock()
    mock_client.complete.return_value = {
        "ships": [
            {"name": "Enterprise", "level": 120, "rarity": "Super Rare", "ship_class": "CV"},
            {"name": "Laffey", "level": 100, "rarity": "Elite", "ship_class": "DD"},
        ]
    }

    result = extract_grid_page(image_path, mock_client)

    assert len(result) == 2
    assert result[0]["name"] == "Enterprise"
    assert result[1]["name"] == "Laffey"
    # source_file must be injected by the function.
    assert result[0]["source_file"] == str(image_path)
    assert result[1]["source_file"] == str(image_path)

    mock_client.complete.assert_called_once()


# ---------------------------------------------------------------------------
# extract_ship_detail — mocked VLMClient
# ---------------------------------------------------------------------------


def test_extract_ship_detail_mock(tmp_path):
    image_path = tmp_path / "000_detail.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)

    mock_client = MagicMock()
    mock_client.complete.return_value = {
        "ship": {
            "name": "Yuudachi",
            "level": 125,
            "rarity": "Elite",
            "ship_class": "DD",
            "affinity": "Love",
            "limit_break": 3,
            "stats": {"firepower": 88, "torpedo": 170},
            "skills": [{"name": "Rocket Torpedo", "level": 10}],
        }
    }

    result = extract_ship_detail(image_path, mock_client)

    assert result["name"] == "Yuudachi"
    assert result["level"] == 125
    assert result["affinity"] == "Love"
    assert result["source_file"] == str(image_path)

    mock_client.complete.assert_called_once()


# ---------------------------------------------------------------------------
# extract_ship_gear — mocked VLMClient
# ---------------------------------------------------------------------------


def test_extract_ship_gear_mock(tmp_path):
    image_path = tmp_path / "000_gear.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)

    mock_client = MagicMock()
    mock_client.complete.return_value = {
        "equipment": [
            {"slot": 1, "name": "Twin 127mm", "level": 10, "rarity": "Gold"},
            {"slot": 2, "name": None, "level": None, "rarity": None},
        ]
    }

    result = extract_ship_gear(image_path, mock_client)

    assert len(result) == 2
    assert result[0]["name"] == "Twin 127mm"
    assert result[0]["source_file"] == str(image_path)
    assert result[1]["name"] is None
    assert result[1]["source_file"] == str(image_path)

    mock_client.complete.assert_called_once()


def test_run_extraction_orchestration(tmp_path):
    capture_dir = tmp_path / "capture"
    grid_dir = capture_dir / "grid"
    ships_dir = capture_dir / "ships"
    grid_dir.mkdir(parents=True)
    ships_dir.mkdir()

    (grid_dir / "page_000.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    (ships_dir / "000_detail.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    (ships_dir / "000_gear.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)

    mock_client = MagicMock()
    mock_client.complete.side_effect = [
        {"ships": [{"name": "Enterprise", "level": 120, "rarity": "Super Rare", "ship_class": "CV"}]},
        {"ship": {"name": "Enterprise", "level": 120, "rarity": "Super Rare", "ship_class": "CV"}},
        {"equipment": [{"slot": 1, "name": "Twin 127mm", "level": 10, "rarity": "Gold"}]},
    ]

    summary = run_extraction(capture_dir, tmp_path / "census.db", mock_client)
    assert summary["grid_pages"] == 1
    assert summary["grid_ships_extracted"] == 1
    assert summary["total_unique_ships"] == 1
    assert summary["equipment_items"] == 1

    conn = sqlite3.connect(str(tmp_path / "census.db"))
    row = conn.execute("SELECT slot_index, name FROM ships ORDER BY slot_index").fetchone()
    conn.close()
    assert row == (0, "Enterprise")


def test_census_extract_main_writes_run_artifacts(tmp_path, monkeypatch):
    capture_dir = tmp_path / "capture"
    capture_dir.mkdir()

    class FakeClient:
        def __init__(self, base_url: str, model: str, timeout_s: int):
            self.base_url = base_url
            self.model = model
            self.timeout_s = timeout_s

    def fake_run_extraction(capture_dir_arg, db_path_arg, client_arg, recorder=None):
        db_path_arg.write_bytes(b"sqlite")
        assert recorder is not None
        return {
            "run_id": 1,
            "capture_dir": str(capture_dir_arg),
            "grid_pages": 0,
            "grid_ships_extracted": 0,
            "detail_pages_processed": 0,
            "total_unique_ships": 0,
            "equipment_items": 0,
        }

    monkeypatch.setattr("scripts.census_extract.VLMClient", FakeClient)
    monkeypatch.setattr("scripts.census_extract.run_extraction", fake_run_extraction)
    monkeypatch.setenv("SC_RUN_DATA_ROOT", str(tmp_path / "runs"))
    monkeypatch.setenv("SC_RUN_SUMMARY_ROOT", str(tmp_path / "summaries"))

    exit_code = main(["--run-id", "extract-run", "extract", str(capture_dir)])
    assert exit_code == 0

    manifest = json.loads((tmp_path / "runs" / "extract-run" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "succeeded"
    assert manifest["output_paths"]["database"].endswith("census.db")
    assert (tmp_path / "runs" / "extract-run" / "events.ndjson").exists()
    assert list((tmp_path / "summaries").glob("*.md"))


def test_census_extract_cli_accepts_model_flags_after_subcommand(tmp_path):
    parser = build_parser()
    args = parser.parse_args(
        [
            "extract",
            str(tmp_path),
            "--base-url",
            "http://localhost:9999/v1",
            "--model",
            "demo-model",
            "--timeout",
            "9",
        ]
    )

    assert args.command == "extract"
    assert args.capture_dir == tmp_path
    assert args.base_url == "http://localhost:9999/v1"
    assert args.model == "demo-model"
    assert args.timeout == 9
