#!/usr/bin/env python3
"""
alas_converter.py — Convert AzurLaneAutoScript page definitions to graph.json.

Reads:
    vendor/AzurLaneAutoScript/module/ui/page.py  (page graph + transitions)
    vendor/AzurLaneAutoScript/module/*/assets.py  (button coordinate/color data)

Writes:
    examples/azur-lane/graph.json  (or --output path)

The converter is purely data-extraction: it does NOT import ALAS Python modules.
All parsing is done with regex against the source text.

Anchor RGB values come from ALAS Button.color[locale] — these are the expected
average pixel colors of the CHECK region. They are real values, not placeholders,
but should still be verified against live screenshots because ALAS color samples
can drift slightly between game versions.
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
ALAS_ROOT = REPO_ROOT / "vendor" / "AzurLaneAutoScript"
PAGE_PY = ALAS_ROOT / "module" / "ui" / "page.py"
OUTPUT = REPO_ROOT / "examples" / "azur-lane" / "graph.json"

# Assets files to scan, in import order from page.py.
ASSETS_FILES = [
    ALAS_ROOT / "module" / "coalition" / "assets.py",
    ALAS_ROOT / "module" / "event_hospital" / "assets.py",
    ALAS_ROOT / "module" / "freebies" / "assets.py",
    ALAS_ROOT / "module" / "raid" / "assets.py",
    ALAS_ROOT / "module" / "retire" / "assets.py",
    ALAS_ROOT / "module" / "ui" / "assets.py",
    ALAS_ROOT / "module" / "ui_white" / "assets.py",
]

# Regex: NAME = Button(area={...}, color={...}, button={...}, ...)
# Each dict value is a shallow locale-keyed dict — no nested braces, so [^}]+ is safe.
_BUTTON_RE = re.compile(
    r"^(\w+)\s*=\s*Button\("
    r"area=(\{[^}]+\}),\s*"
    r"color=(\{[^}]+\}),\s*"
    r"button=(\{[^}]+\})",
    re.MULTILINE,
)

# Regex: page_XXX = Page(BUTTON_NAME)  or  Page(None)
_PAGE_RE = re.compile(r"^(page_\w+)\s*=\s*Page\((\w+)\)", re.MULTILINE)

# Regex: page_XXX.link(button=BTN, destination=page_YYY)
_LINK_RE = re.compile(
    r"^(page_\w+)\.link\(button=(\w+),\s*destination=(page_\w+)\)",
    re.MULTILINE,
)

_LABEL_ALIASES = {
    # Upstream ALAS uses this misspelling as an identifier, but the generated
    # graph label is user-facing and should read cleanly.
    "HOSIPITAL_CHECK": "HOSPITAL_CHECK",
}


# ---------------------------------------------------------------------------
# Button loading
# ---------------------------------------------------------------------------


def _parse_locale_dict(raw: str) -> dict[str, Any]:
    """Parse a Python dict literal like {'cn': (1,2,3,4), 'en': ...}."""
    return ast.literal_eval(raw)


def load_buttons(locale: str = "en") -> dict[str, dict[str, Any]]:
    """
    Parse all relevant ALAS assets files and return:
        {button_name: {area: (x1,y1,x2,y2), color: (r,g,b), button: (x1,y1,x2,y2)}}
    using the specified locale, falling back to 'cn' if locale is missing.
    """
    buttons: dict[str, dict[str, Any]] = {}
    for path in ASSETS_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for m in _BUTTON_RE.finditer(text):
            name = m.group(1)
            try:
                area_d = _parse_locale_dict(m.group(2))
                color_d = _parse_locale_dict(m.group(3))
                button_d = _parse_locale_dict(m.group(4))
            except (ValueError, SyntaxError):
                continue
            fallback = "cn"
            buttons[name] = {
                "area": area_d.get(locale) or area_d.get(fallback),
                "color": color_d.get(locale) or color_d.get(fallback),
                "button": button_d.get(locale) or button_d.get(fallback),
            }
    return buttons


def ensure_alas_sources_present() -> None:
    """Raise a helpful error if the checked-out ALAS source tree is unavailable."""
    if not PAGE_PY.exists():
        raise FileNotFoundError(
            f"{PAGE_PY} not found.\n"
            "Make sure the ALAS submodule is checked out:\n"
            "  git submodule update --init vendor/AzurLaneAutoScript"
        )


def display_button_name(name: str) -> str:
    """Return a user-facing button label for generated graph metadata."""
    return _LABEL_ALIASES.get(name, name)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def region_center(region: tuple[int, int, int, int]) -> tuple[int, int]:
    """Return the integer center (x, y) of an (x1, y1, x2, y2) region."""
    x1, y1, x2, y2 = region
    return (x1 + x2) // 2, (y1 + y2) // 2


# ---------------------------------------------------------------------------
# Page graph parsing
# ---------------------------------------------------------------------------


def parse_page_graph(
    buttons: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Parse module/ui/page.py to extract page and transition data.

    Returns (states_dict, transitions_dict) ready for graph.json.
    """
    ensure_alas_sources_present()
    text = PAGE_PY.read_text(encoding="utf-8")

    # Strip pure-comment lines so commented-out page defs aren't picked up.
    clean_lines = [ln for ln in text.splitlines() if not re.match(r"^\s*#", ln)]
    clean = "\n".join(clean_lines)

    # --- Pages ---
    pages: dict[str, str | None] = {}
    for m in _PAGE_RE.finditer(clean):
        name = m.group(1)
        check_btn = m.group(2)
        pages[name] = None if check_btn == "None" else check_btn

    # --- Raw transitions ---
    raw_links: list[dict[str, str]] = []
    for m in _LINK_RE.finditer(clean):
        raw_links.append({"source": m.group(1), "button": m.group(2), "dest": m.group(3)})

    # --- Build states ---
    states: dict[str, Any] = {}
    for page_name, check_btn in pages.items():
        human = page_name.replace("page_", "").replace("_", " ").title()
        desc = f"{human} page (Azur Lane)"
        anchors: list[dict[str, Any]] = []
        if check_btn and check_btn in buttons:
            btn = buttons[check_btn]
            cx, cy = region_center(btn["area"])
            r, g, b = btn["color"]
            anchors.append(
                {
                    "type": "pixel_color",
                    "x": cx,
                    "y": cy,
                    "expected_rgb": [r, g, b],
                    "cost": 1,
                    "label": f"{display_button_name(check_btn)} — check region center",
                }
            )
        states[page_name] = {
            "description": desc,
            "anchors": anchors,
            "confidence_threshold": 0.7,
        }

    # --- Build transitions ---
    transitions: dict[str, Any] = {}
    pair_count: dict[tuple[str, str], int] = {}

    for link in raw_links:
        source = link["source"]
        dest = link["dest"]
        btn_name = link["button"]

        # Skip references to pages not defined in page.py (shouldn't happen, but be safe)
        if source not in pages or dest not in pages:
            continue

        pair = (source, dest)
        idx = pair_count.get(pair, 0)
        pair_count[pair] = idx + 1

        src_short = source.removeprefix("page_")
        dst_short = dest.removeprefix("page_")
        key = f"{src_short}_to_{dst_short}" if idx == 0 else f"{src_short}_to_{dst_short}_{idx}"

        if btn_name in buttons:
            cx, cy = region_center(buttons[btn_name]["button"])
            action: dict[str, Any] = {"type": "adb_tap", "x": cx, "y": cy}
        else:
            # Button not found in any scanned assets file — use zero coords as sentinel
            action = {"type": "adb_tap", "x": 0, "y": 0}

        transitions[key] = {
            "source": source,
            "dest": dest,
            "method": "deterministic",
            "cost": 10,
            "action": action,
        }

    return states, transitions


# ---------------------------------------------------------------------------
# Top-level builder
# ---------------------------------------------------------------------------


def build_graph(locale: str = "en", serial: str = "127.0.0.1:21513") -> dict[str, Any]:
    """Build a complete graph.json dict from ALAS source data."""
    ensure_alas_sources_present()
    buttons = load_buttons(locale)
    states, transitions = parse_page_graph(buttons)
    return {
        "initial_state": "page_main",
        "metadata": {
            "app": "Azur Lane",
            "emulator": "MEMU",
            "resolution": "1280x720",
            "adb_serial": serial,
            "locale": locale,
            "source": "Generated by scripts/alas_converter.py from AzurLaneAutoScript",
            "note": (
                "expected_rgb values sampled from ALAS Button.color — "
                "verify against live screenshots before relying on them"
            ),
        },
        "states": states,
        "transitions": transitions,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert ALAS page definitions to State Cartographer graph.json")
    parser.add_argument(
        "--locale",
        default="en",
        choices=["cn", "en", "jp", "tw"],
        help="Locale to use for button coordinates and colors (default: en)",
    )
    parser.add_argument(
        "--serial",
        default="127.0.0.1:21513",
        help="ADB serial to embed in metadata (default: 127.0.0.1:21513)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT,
        help=f"Output path (default: {OUTPUT})",
    )
    args = parser.parse_args()

    try:
        ensure_alas_sources_present()
    except FileNotFoundError as exc:
        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    graph = build_graph(locale=args.locale, serial=args.serial)

    out_path: Path = args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")

    n_states = len(graph["states"])
    n_transitions = len(graph["transitions"])
    missing_anchors = sum(1 for s in graph["states"].values() if not s["anchors"])
    missing_actions = sum(1 for t in graph["transitions"].values() if t["action"]["x"] == 0 and t["action"]["y"] == 0)
    print(f"Wrote {out_path}")
    print(f"  states:      {n_states}")
    print(f"  transitions: {n_transitions}")
    if missing_anchors:
        print(f"  WARNING: {missing_anchors} states have no anchors (check_button not found)")
    if missing_actions:
        print(f"  WARNING: {missing_actions} transitions have zero-coord action (button not found)")


if __name__ == "__main__":
    main()
