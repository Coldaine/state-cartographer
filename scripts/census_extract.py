"""Offline VLM extraction pipeline for dock census screenshots.

Processes Azur Lane dock census captures (grid pages, ship detail pages,
and gear pages) through a local VLM and stores structured results in a
SQLite database.

Capture directory layout expected::

    data/census/{timestamp}/
        grid/
            page_000.png
            page_001.png
            ...
        ships/
            000_detail.png
            000_gear.png
            001_detail.png
            ...

Usage::

    python scripts/census_extract.py extract data/census/2026-04-04_120000/
    python scripts/census_extract.py extract data/census/2026-04-04_120000/ --db data/census/census.db
    python scripts/census_extract.py extract data/census/2026-04-04_120000/ --base-url http://localhost:18900/v1 --model local-vlm
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import mimetypes
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

import requests

log = logging.getLogger(__name__)

DEFAULT_BASE_URL = os.getenv("SC_VLM_BASE_URL", "http://localhost:18900/v1")
DEFAULT_MODEL = os.getenv("SC_VLM_MODEL", "local-vlm")

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a strict screenshot analysis assistant for Azur Lane.

Use only the information visible in the provided screenshot.
Prefer explicit uncertainty over confident guessing.
Return JSON that matches the requested schema exactly."""

GRID_EXTRACT_PROMPT = """Analyze this Azur Lane dock grid screenshot.

List every ship visible in the grid. For each ship, extract:
- name: the ship's name (text visible on the card)
- level: the level number (Lv. XX)
- rarity: the rarity tier based on card border color (Normal/Rare/Elite/Super Rare/Ultra Rare/Decisive/Priority)
- ship_class: the class icon if identifiable (DD/CL/CA/BB/CV/etc.)

Return a JSON object with a single key "ships" containing an array of objects.
Example: {"ships": [{"name": "Enterprise", "level": 120, "rarity": "Super Rare", "ship_class": "CV"}, ...]}

If a field cannot be determined, use null. Include EVERY ship visible, even if partially cut off at edges."""

DETAIL_EXTRACT_PROMPT = """Analyze this Azur Lane ship detail screenshot.

Extract the following information:
- name: ship name
- level: current level (Lv. XX)
- rarity: rarity tier
- ship_class: ship class (DD/CL/CA/BB/CV/etc.)
- affinity: affinity value or heart status if visible
- stats: any visible combat stats (firepower, torpedo, aviation, etc.)
- skills: skill names and levels if visible
- limit_break: limit break stars (0-4)

Return as JSON: {"ship": {"name": ..., "level": ..., "rarity": ..., "ship_class": ..., "affinity": ..., "limit_break": ..., "stats": {...}, "skills": [...]}}
Use null for any field that cannot be determined."""

GEAR_EXTRACT_PROMPT = """Analyze this Azur Lane ship equipment/gear screenshot.

List every equipped gear item visible. For each slot, extract:
- slot: slot number (1-6, or "augment" for augment module)
- name: equipment name
- level: enhancement level (+0 to +13)
- rarity: rarity tier based on color

Return as JSON: {"equipment": [{"slot": 1, "name": "Twin 127mm", "level": 10, "rarity": "Gold"}, ...]}
Include empty slots as {"slot": N, "name": null, "level": null, "rarity": null}.
Use null for any field that cannot be determined."""

# ---------------------------------------------------------------------------
# VLM helpers (self-contained, mirrors vlm_detector.py patterns)
# ---------------------------------------------------------------------------


def _image_to_data_url(image_path: Path) -> str:
    """Encode an image file as a base64 data URL."""
    mime, _ = mimetypes.guess_type(image_path.name)
    mime = mime or "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _build_messages(prompt: str, image_path: Path) -> list[dict[str, Any]]:
    """Build an OpenAI-compatible message list with one image."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": _image_to_data_url(image_path)},
                },
            ],
        },
    ]


def _extract_message_text(payload: dict[str, Any]) -> str:
    """Pull the text content out of an OpenAI-style chat completion."""
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError("VLM response did not include choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = [item.get("text", "") for item in content if item.get("type") == "text"]
        return "\n".join(part for part in texts if part)
    raise ValueError("VLM response content was not understood")


def _parse_json_response(text: str) -> dict[str, Any]:
    """Parse JSON from VLM output, stripping markdown code fences if present."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
    return json.loads(stripped)


# ---------------------------------------------------------------------------
# VLM client
# ---------------------------------------------------------------------------


class VLMClient:
    """Small OpenAI-compatible client for census extraction."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout_s: int = 120,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    def complete(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Send a chat completion request and return parsed JSON."""
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": messages,
                "response_format": {"type": "json_object"},
            },
            timeout=self.timeout_s,
        )
        response.raise_for_status()
        payload = response.json()
        return _parse_json_response(_extract_message_text(payload))


# ---------------------------------------------------------------------------
# SQLite persistence
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS census_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    capture_dir TEXT NOT NULL,
    grid_pages INTEGER,
    ships_processed INTEGER,
    status TEXT DEFAULT 'in_progress'
);

CREATE TABLE IF NOT EXISTS ships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    census_run_id INTEGER NOT NULL REFERENCES census_runs(id),
    name TEXT,
    level INTEGER,
    rarity TEXT,
    ship_class TEXT,
    affinity TEXT,
    limit_break INTEGER,
    stats_json TEXT,
    skills_json TEXT,
    source_file TEXT,
    UNIQUE(census_run_id, name)
);

CREATE TABLE IF NOT EXISTS equipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ship_id INTEGER NOT NULL REFERENCES ships(id),
    slot TEXT,
    name TEXT,
    level INTEGER,
    rarity TEXT,
    source_file TEXT
);
"""


class CensusDB:
    """Thin wrapper around the census SQLite database."""

    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(str(db_path))
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        """Create tables if they do not already exist."""
        self.conn.executescript(_SCHEMA_SQL)

    def start_run(self, capture_dir: str, grid_pages: int, ships_processed: int) -> int:
        """Insert a new census run and return the run id."""
        timestamp = Path(capture_dir).name
        cur = self.conn.execute(
            "INSERT INTO census_runs (timestamp, capture_dir, grid_pages, ships_processed, status) "
            "VALUES (?, ?, ?, ?, 'in_progress')",
            (timestamp, capture_dir, grid_pages, ships_processed),
        )
        self.conn.commit()
        assert cur.lastrowid is not None
        return cur.lastrowid

    def complete_run(self, run_id: int) -> None:
        """Mark a census run as complete and update the ship count."""
        count = self.conn.execute("SELECT COUNT(*) FROM ships WHERE census_run_id = ?", (run_id,)).fetchone()[0]
        self.conn.execute(
            "UPDATE census_runs SET status = 'complete', ships_processed = ? WHERE id = ?",
            (count, run_id),
        )
        self.conn.commit()

    def upsert_ship(self, run_id: int, ship_data: dict[str, Any]) -> int:
        """Insert or update a ship record, deduplicating by name within the run.

        Returns the canonical ship id (looked up after upsert, not lastrowid
        which is unreliable on ON CONFLICT DO UPDATE).
        """
        stats_json = json.dumps(ship_data.get("stats")) if ship_data.get("stats") else None
        skills_json = json.dumps(ship_data.get("skills")) if ship_data.get("skills") else None

        self.conn.execute(
            "INSERT INTO ships (census_run_id, name, level, rarity, ship_class, "
            "affinity, limit_break, stats_json, skills_json, source_file) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(census_run_id, name) DO UPDATE SET "
            "level = COALESCE(excluded.level, ships.level), "
            "rarity = COALESCE(excluded.rarity, ships.rarity), "
            "ship_class = COALESCE(excluded.ship_class, ships.ship_class), "
            "affinity = COALESCE(excluded.affinity, ships.affinity), "
            "limit_break = COALESCE(excluded.limit_break, ships.limit_break), "
            "stats_json = COALESCE(excluded.stats_json, ships.stats_json), "
            "skills_json = COALESCE(excluded.skills_json, ships.skills_json), "
            "source_file = COALESCE(excluded.source_file, ships.source_file)",
            (
                run_id,
                ship_data.get("name"),
                ship_data.get("level"),
                ship_data.get("rarity"),
                ship_data.get("ship_class"),
                str(ship_data["affinity"]) if ship_data.get("affinity") is not None else None,
                ship_data.get("limit_break"),
                stats_json,
                skills_json,
                ship_data.get("source_file"),
            ),
        )
        row = self.conn.execute(
            "SELECT id FROM ships WHERE census_run_id = ? AND name = ?",
            (run_id, ship_data.get("name")),
        ).fetchone()
        assert row is not None, f"ship not found after upsert: {ship_data.get('name')}"
        return row[0]

    def add_equipment(self, ship_id: int, equip_data: dict[str, Any]) -> None:
        """Insert a single equipment record for a ship."""
        self.conn.execute(
            "INSERT INTO equipment (ship_id, slot, name, level, rarity, source_file) VALUES (?, ?, ?, ?, ?, ?)",
            (
                ship_id,
                str(equip_data.get("slot")) if equip_data.get("slot") is not None else None,
                equip_data.get("name"),
                equip_data.get("level"),
                equip_data.get("rarity"),
                equip_data.get("source_file"),
            ),
        )

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()


# ---------------------------------------------------------------------------
# Extraction functions
# ---------------------------------------------------------------------------


def extract_grid_page(image_path: Path, client: VLMClient) -> list[dict[str, Any]]:
    """Extract ship summaries from a grid screenshot.

    Returns a list of dicts, one per ship found on the page.
    """
    messages = _build_messages(GRID_EXTRACT_PROMPT, image_path)
    result = client.complete(messages)
    ships = result.get("ships") or []
    for ship in ships:
        ship["source_file"] = str(image_path)
    return ships


def extract_ship_detail(image_path: Path, client: VLMClient) -> dict[str, Any]:
    """Extract detailed ship info from a detail screenshot.

    Returns a single ship dict.
    """
    messages = _build_messages(DETAIL_EXTRACT_PROMPT, image_path)
    result = client.complete(messages)
    ship = result.get("ship") or {}
    ship["source_file"] = str(image_path)
    return ship


def extract_ship_gear(image_path: Path, client: VLMClient) -> list[dict[str, Any]]:
    """Extract equipment info from a gear screenshot.

    Returns a list of equipment dicts.
    """
    messages = _build_messages(GEAR_EXTRACT_PROMPT, image_path)
    result = client.complete(messages)
    equipment = result.get("equipment") or []
    for item in equipment:
        item["source_file"] = str(image_path)
    return equipment


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

_SHIP_INDEX_RE = re.compile(r"^(\d+)_(detail|gear)\.png$")


def _discover_capture_dir(capture_dir: Path) -> tuple[list[Path], dict[str, dict[str, Path]]]:
    """Discover grid pages and per-ship screenshot paths.

    Returns:
        grid_pages: sorted list of grid page image paths
        ship_files: dict mapping ship index string -> {"detail": Path, "gear": Path}
    """
    grid_dir = capture_dir / "grid"
    ships_dir = capture_dir / "ships"

    grid_pages: list[Path] = []
    if grid_dir.is_dir():
        grid_pages = sorted(grid_dir.glob("page_*.png"))

    ship_files: dict[str, dict[str, Path]] = {}
    if ships_dir.is_dir():
        for f in sorted(ships_dir.iterdir()):
            m = _SHIP_INDEX_RE.match(f.name)
            if m:
                idx, kind = m.group(1), m.group(2)
                ship_files.setdefault(idx, {})[kind] = f

    return grid_pages, ship_files


def run_extraction(
    capture_dir: Path,
    db_path: Path,
    client: VLMClient,
) -> dict[str, Any]:
    """Process all screenshots in a capture directory.

    Workflow:
        1. Discover grid pages and per-ship screenshots.
        2. Start a census run in the database.
        3. Extract grid pages to get initial ship list.
        4. Extract detail and gear pages to enrich ship records.
        5. Complete the run and return summary stats.
    """
    grid_pages, ship_files = _discover_capture_dir(capture_dir)
    log.info(
        "Discovered %d grid pages and %d ship screenshot sets in %s",
        len(grid_pages),
        len(ship_files),
        capture_dir,
    )

    db = CensusDB(db_path)
    try:
        run_id = db.start_run(
            capture_dir=str(capture_dir),
            grid_pages=len(grid_pages),
            ships_processed=0,
        )

        # -- Phase 1: grid pages ------------------------------------------------
        grid_ship_count = 0
        for i, page_path in enumerate(grid_pages, 1):
            log.info("Extracting grid page %d/%d...", i, len(grid_pages))
            try:
                ships = extract_grid_page(page_path, client)
            except Exception:
                log.exception("Failed to extract grid page %s", page_path)
                continue
            for ship in ships:
                if not ship.get("name"):
                    continue
                db.upsert_ship(run_id, ship)
                grid_ship_count += 1
        db.conn.commit()

        # -- Phase 2: detail + gear pages ----------------------------------------
        equipment_count = 0
        for i, (idx, files) in enumerate(sorted(ship_files.items()), 1):
            log.info("Extracting ship %d/%d...", i, len(ship_files))

            # Detail
            detail_path = files.get("detail")
            if detail_path:
                try:
                    detail = extract_ship_detail(detail_path, client)
                except Exception:
                    log.exception("Failed to extract detail for ship %s", detail_path)
                    detail = {}
            else:
                detail = {}

            if not detail.get("name"):
                log.warning("No name extracted for ship index %s, skipping", idx)
                continue

            ship_id = db.upsert_ship(run_id, detail)

            # Gear
            gear_path = files.get("gear")
            if gear_path:
                try:
                    gear_items = extract_ship_gear(gear_path, client)
                except Exception:
                    log.exception("Failed to extract gear for ship %s", gear_path)
                    gear_items = []
                for item in gear_items:
                    db.add_equipment(ship_id, item)
                    equipment_count += 1

        db.conn.commit()

        # -- Finalize ------------------------------------------------------------
        db.complete_run(run_id)

        total_ships = db.conn.execute("SELECT COUNT(*) FROM ships WHERE census_run_id = ?", (run_id,)).fetchone()[0]

        summary = {
            "run_id": run_id,
            "capture_dir": str(capture_dir),
            "grid_pages": len(grid_pages),
            "grid_ships_extracted": grid_ship_count,
            "detail_pages_processed": len(ship_files),
            "total_unique_ships": total_ships,
            "equipment_items": equipment_count,
        }
        return summary
    finally:
        db.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for census_extract."""
    parser = argparse.ArgumentParser(
        description="Offline VLM extraction pipeline for Azur Lane dock census screenshots.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="OpenAI-compatible VLM base URL (default: %(default)s).",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="VLM model name (default: %(default)s).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="VLM request timeout in seconds (default: %(default)s).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser(
        "extract",
        help="Process a census capture directory through the VLM and store results.",
    )
    extract_parser.add_argument(
        "capture_dir",
        type=Path,
        help="Path to the capture directory (e.g. data/census/2026-04-04_120000/).",
    )
    extract_parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="SQLite database path (default: <capture_dir>/../census.db).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the census extraction CLI."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = build_parser()
    args = parser.parse_args(argv)

    client = VLMClient(base_url=args.base_url, model=args.model, timeout_s=args.timeout)

    if args.command == "extract":
        capture_dir = args.capture_dir.resolve()
        if not capture_dir.is_dir():
            log.error("Capture directory does not exist: %s", capture_dir)
            return 1

        db_path: Path = args.db if args.db else capture_dir.parent / "census.db"
        db_path = db_path.resolve()
        log.info("Capture directory: %s", capture_dir)
        log.info("Database: %s", db_path)

        summary = run_extraction(capture_dir, db_path, client)

        print("\n--- Census Extraction Summary ---")
        print(f"  Run ID:               {summary['run_id']}")
        print(f"  Capture directory:     {summary['capture_dir']}")
        print(f"  Grid pages processed:  {summary['grid_pages']}")
        print(f"  Ships from grid:       {summary['grid_ships_extracted']}")
        print(f"  Detail pages:          {summary['detail_pages_processed']}")
        print(f"  Total unique ships:    {summary['total_unique_ships']}")
        print(f"  Equipment items:       {summary['equipment_items']}")
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
