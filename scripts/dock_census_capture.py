#!/usr/bin/env python3
"""Dock census capture pipeline for Azur Lane.

Captures the full dock inventory via two complementary modes:

  grid_scan  -- screenshot every page of the dock grid (fast overview).
  deep_dive  -- tap into each ship for detail + gear screenshots.

Both modes auto-detect scroll-end by comparing consecutive raw PNG bytes
(Vulkan renders identically at the same scroll position).

Usage:
    uv run python scripts/dock_census_capture.py grid-scan
    uv run python scripts/dock_census_capture.py deep-dive --limit 10
    uv run python scripts/dock_census_capture.py grid-scan --config configs/memu.json
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from state_cartographer.transport.pilot import Pilot

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Repo paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


# ---------------------------------------------------------------------------
# DockLayout — calibration constants for the 1280x720 dock grid
# ---------------------------------------------------------------------------


@dataclass
class DockLayout:
    """Calibration constants for dock grid at 1280x720."""

    # Navigation
    dock_tap: tuple[int, int] = (249, 680)
    back_tap: tuple[int, int] = (57, 55)
    nav_wait: float = 2.0

    # Grid area bounds
    grid_left: int = 0
    grid_top: int = 94
    grid_right: int = 1280
    grid_bottom: int = 648
    columns: int = 8
    visible_rows: int = 3

    # Swipe calibration
    swipe_x: int = 640
    swipe_start_y: int = 580
    swipe_end_y: int = 200
    swipe_duration_ms: int = 500
    swipe_settle: float = 1.0

    # Deep dive
    gear_tab_tap: tuple[int, int] = (980, 140)
    detail_wait: float = 1.5
    gear_wait: float = 1.0
    back_wait: float = 1.0

    @property
    def cell_width(self) -> int:
        return (self.grid_right - self.grid_left) // self.columns

    @property
    def cell_height(self) -> int:
        return (self.grid_bottom - self.grid_top) // self.visible_rows


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_output_dir() -> Path:
    """Create a timestamped census output directory."""
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out = DATA_DIR / "census" / stamp
    out.mkdir(parents=True, exist_ok=True)
    return out


def _detect_scroll_end(prev_bytes: bytes, curr_bytes: bytes) -> bool:
    """Return True if raw PNG bytes are identical (scroll has stopped)."""
    return prev_bytes == curr_bytes


def _navigate_to_dock(pilot: Pilot, layout: DockLayout) -> None:
    """Tap from page_main into page_dock and wait for the transition."""
    log.info("Navigating to dock: tap(%d, %d)", *layout.dock_tap)
    if not pilot.tap(*layout.dock_tap):
        raise RuntimeError(f"Failed to navigate to dock: tap{layout.dock_tap} unsuccessful")
    time.sleep(layout.nav_wait)


# ---------------------------------------------------------------------------
# grid_scan
# ---------------------------------------------------------------------------


def grid_scan(
    pilot: Pilot,
    output_dir: Path,
    layout: DockLayout | None = None,
) -> dict[str, int | float]:
    """Capture every page of the dock grid by repeated swipe-and-screenshot.

    Args:
        pilot: Connected Pilot instance.
        output_dir: Root census directory. Grid pages go into ``output_dir/grid/``.
        layout: Optional calibration overrides.

    Returns:
        Dict with ``total_screenshots`` and ``elapsed_seconds``.
    """
    if layout is None:
        layout = DockLayout()

    grid_dir = output_dir / "grid"
    grid_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.monotonic()

    # Navigate to dock
    _navigate_to_dock(pilot, layout)

    # Capture first page
    index = 0
    page_path = grid_dir / f"page_{index:03d}.png"
    prev_bytes = pilot.screenshot()
    page_path.write_bytes(prev_bytes)
    log.info("Saved %s", page_path.name)
    index += 1

    # Scroll and capture until end
    while True:
        pilot.swipe(
            layout.swipe_x,
            layout.swipe_start_y,
            layout.swipe_x,
            layout.swipe_end_y,
            layout.swipe_duration_ms,
        )
        time.sleep(layout.swipe_settle)

        curr_bytes = pilot.screenshot()

        if _detect_scroll_end(prev_bytes, curr_bytes):
            log.info("Scroll end detected after %d pages", index)
            break

        page_path = grid_dir / f"page_{index:03d}.png"
        page_path.write_bytes(curr_bytes)
        log.info("Saved %s", page_path.name)

        prev_bytes = curr_bytes
        index += 1

    elapsed = time.monotonic() - t0
    return {"total_screenshots": index, "elapsed_seconds": round(elapsed, 2)}


# ---------------------------------------------------------------------------
# deep_dive
# ---------------------------------------------------------------------------


def deep_dive(
    pilot: Pilot,
    output_dir: Path,
    layout: DockLayout | None = None,
    limit: int | None = None,
) -> dict[str, int | float]:
    """Tap into each ship for detail and gear screenshots.

    Iterates row-by-row across the visible grid, scrolls when all visible
    rows are exhausted, and stops when the grid can no longer scroll or
    ``limit`` ships have been processed.

    Args:
        pilot: Connected Pilot instance.
        output_dir: Root census directory. Ships go into ``output_dir/ships/``.
        layout: Optional calibration overrides.
        limit: Stop after this many ships. None means capture all.

    Returns:
        Dict with ``total_ships``, ``total_screenshots``, and ``elapsed_seconds``.
    """
    if layout is None:
        layout = DockLayout()

    ships_dir = output_dir / "ships"
    ships_dir.mkdir(parents=True, exist_ok=True)

    cell_width = layout.cell_width
    cell_height = layout.cell_height

    t0 = time.monotonic()
    ship_index = 0
    screenshot_count = 0

    # Navigate to dock
    _navigate_to_dock(pilot, layout)

    # Capture a baseline for scroll-end detection
    prev_grid_bytes = pilot.screenshot()

    while True:
        # Process each visible row, then each column in that row
        for row in range(layout.visible_rows):
            for col in range(layout.columns):
                if limit is not None and ship_index >= limit:
                    log.info("Limit of %d ships reached", limit)
                    elapsed = time.monotonic() - t0
                    return {
                        "total_ships": ship_index,
                        "total_screenshots": screenshot_count,
                        "elapsed_seconds": round(elapsed, 2),
                    }

                cx = layout.grid_left + col * cell_width + cell_width // 2
                cy = layout.grid_top + row * cell_height + cell_height // 2

                # 1. Tap ship cell
                log.info("Ship %03d: tap(%d, %d) [col=%d, row=%d]", ship_index, cx, cy, col, row)
                if not pilot.tap(cx, cy):
                    log.error("Tap failed at (%d, %d), stopping capture", cx, cy)
                    raise RuntimeError(f"Tap failed at ({cx}, {cy})")
                time.sleep(layout.detail_wait)

                # 2. Detail screenshot
                detail_path = ships_dir / f"{ship_index:03d}_detail.png"
                detail_path.write_bytes(pilot.screenshot())
                screenshot_count += 1
                log.info("  -> %s", detail_path.name)

                # 3. Tap gear/equipment tab
                if not pilot.tap(*layout.gear_tab_tap):
                    log.error("Gear tab tap failed, stopping capture")
                    raise RuntimeError(f"Gear tab tap failed at {layout.gear_tab_tap}")
                time.sleep(layout.gear_wait)

                # 4. Gear screenshot
                gear_path = ships_dir / f"{ship_index:03d}_gear.png"
                gear_path.write_bytes(pilot.screenshot())
                screenshot_count += 1
                log.info("  -> %s", gear_path.name)

                # 5. Back to dock grid
                if not pilot.tap(*layout.back_tap):
                    log.error("Back button tap failed, stopping capture")
                    raise RuntimeError(f"Back tap failed at {layout.back_tap}")
                time.sleep(layout.back_wait)

                ship_index += 1

        # All visible rows processed — swipe to next page
        pilot.swipe(
            layout.swipe_x,
            layout.swipe_start_y,
            layout.swipe_x,
            layout.swipe_end_y,
            layout.swipe_duration_ms,
        )
        time.sleep(layout.swipe_settle)

        curr_grid_bytes = pilot.screenshot()

        if _detect_scroll_end(prev_grid_bytes, curr_grid_bytes):
            log.info("Scroll end detected after %d ships", ship_index)
            break

        prev_grid_bytes = curr_grid_bytes

    elapsed = time.monotonic() - t0
    return {
        "total_ships": ship_index,
        "total_screenshots": screenshot_count,
        "elapsed_seconds": round(elapsed, 2),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dock census capture pipeline for Azur Lane.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # grid-scan
    gs = sub.add_parser("grid-scan", help="Screenshot every page of the dock grid.")
    gs.add_argument("--config", type=str, default=None, help="Path to transport config JSON (e.g. configs/memu.json).")

    # deep-dive
    dd = sub.add_parser("deep-dive", help="Tap into each ship for detail + gear screenshots.")
    dd.add_argument("--limit", type=int, default=None, help="Stop after N ships.")
    dd.add_argument("--config", type=str, default=None, help="Path to transport config JSON (e.g. configs/memu.json).")

    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    args = _build_parser().parse_args()
    output_dir = _make_output_dir()
    layout = DockLayout()

    log.info("Output directory: %s", output_dir)

    with Pilot(config_path=args.config) as pilot:
        if args.command == "grid-scan":
            result = grid_scan(pilot, output_dir, layout)
        elif args.command == "deep-dive":
            result = deep_dive(pilot, output_dir, layout, limit=args.limit)
        else:
            log.error("Unknown command: %s", args.command)
            sys.exit(1)

    # Summary
    print("\n--- Census Summary ---")
    for key, value in result.items():
        print(f"  {key}: {value}")
    print(f"  output_dir: {output_dir}")
    print("----------------------")


if __name__ == "__main__":
    main()
