"""Tests for observe.py — Observation Extractor."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from png_factory import make_rgb_png

from observe import build_observations, extract_pixel_coords

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"


class TestExtractPixelCoords:
    def test_extracts_from_pixel_color_anchors(self):
        graph = {
            "states": {
                "s1": {
                    "anchors": [
                        {"type": "pixel_color", "x": 100, "y": 200, "expected_rgb": [255, 0, 0]},
                        {"type": "pixel_color", "x": 50, "y": 30, "expected_rgb": [0, 255, 0]},
                    ]
                }
            },
            "transitions": {},
        }
        coords = extract_pixel_coords(graph)
        assert (50, 30) in coords
        assert (100, 200) in coords

    def test_ignores_non_pixel_anchors(self):
        graph = {
            "states": {
                "s1": {
                    "anchors": [
                        {"type": "text_match", "pattern": "Hello"},
                        {"type": "dom_element", "selector": "#el"},
                    ]
                }
            },
            "transitions": {},
        }
        coords = extract_pixel_coords(graph)
        assert coords == []

    def test_extracts_from_negative_anchors_too(self):
        graph = {
            "states": {
                "s1": {
                    "anchors": [],
                    "negative_anchors": [
                        {"type": "pixel_color", "x": 10, "y": 20, "expected_rgb": [0, 0, 0]},
                    ],
                }
            },
            "transitions": {},
        }
        coords = extract_pixel_coords(graph)
        assert (10, 20) in coords

    def test_deduplicates_coords(self):
        graph = {
            "states": {
                "s1": {
                    "anchors": [
                        {"type": "pixel_color", "x": 5, "y": 5, "expected_rgb": [255, 0, 0]},
                    ]
                },
                "s2": {
                    "anchors": [
                        {"type": "pixel_color", "x": 5, "y": 5, "expected_rgb": [0, 255, 0]},
                    ]
                },
            },
            "transitions": {},
        }
        coords = extract_pixel_coords(graph)
        assert coords.count((5, 5)) == 1

    def test_empty_graph(self):
        graph = {"states": {}, "transitions": {}}
        coords = extract_pixel_coords(graph)
        assert coords == []


class TestBuildObservations:
    def test_records_screenshot_path(self, tmp_path):
        screenshot = tmp_path / "screen.png"
        screenshot.write_bytes(b"fake")
        obs = build_observations(screenshot, [])
        assert obs["screenshot"] == str(screenshot.resolve())

    def test_empty_pixels_when_no_coords(self, tmp_path):
        screenshot = tmp_path / "screen.png"
        screenshot.write_bytes(b"fake")
        obs = build_observations(screenshot, [])
        assert obs["pixels"] == {}

    def test_default_fields_present(self, tmp_path):
        screenshot = tmp_path / "screen.png"
        screenshot.write_bytes(b"fake")
        obs = build_observations(screenshot)
        assert "screenshot" in obs
        assert "pixels" in obs
        assert "text_content" in obs
        assert "dom_elements" in obs
        assert obs["text_content"] is None
        assert obs["dom_elements"] == []

    def test_pixel_extraction_from_real_image(self, tmp_path):
        # 2x2 image: (0,0)=red, (1,0)=green, (0,1)=blue, (1,1)=white
        pixels = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)]
        png_bytes = make_rgb_png(pixels, width=2, height=2)
        screenshot = tmp_path / "real.png"
        screenshot.write_bytes(png_bytes)

        pil = pytest.importorskip("PIL", reason="Pillow not installed")  # noqa: F841

        obs = build_observations(screenshot, [(0, 0), (1, 0), (0, 1)])
        assert obs["pixels"].get("0,0") == [255, 0, 0]
        assert obs["pixels"].get("1,0") == [0, 255, 0]
        assert obs["pixels"].get("0,1") == [0, 0, 255]
        # (1,1) was not requested — should not appear
        assert "1,1" not in obs["pixels"]


class TestObserveCLI:
    def run_observe(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "observe.py"), *args],
            capture_output=True,
            text=True,
            timeout=15,
        )

    def test_missing_screenshot_returns_exit_2(self, tmp_path):
        result = self.run_observe("--screenshot", str(tmp_path / "nonexistent.png"))
        assert result.returncode == 2
        assert "not found" in result.stderr.lower() or "file not found" in result.stderr.lower()

    def test_missing_graph_returns_exit_2(self, tmp_path):
        screenshot = tmp_path / "screen.png"
        screenshot.write_bytes(b"fake")
        result = self.run_observe("--screenshot", str(screenshot), "--graph", str(tmp_path / "missing.json"))
        assert result.returncode == 2

    def test_valid_screenshot_no_graph_outputs_json(self, tmp_path):
        screenshot = tmp_path / "screen.png"
        screenshot.write_bytes(b"fake png data")
        result = self.run_observe("--screenshot", str(screenshot))
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "screenshot" in data
        assert "pixels" in data
        assert "text_content" in data

    def test_output_to_file(self, tmp_path):
        screenshot = tmp_path / "screen.png"
        screenshot.write_bytes(b"fake png data")
        output_file = tmp_path / "obs.json"
        result = self.run_observe("--screenshot", str(screenshot), "--output", str(output_file))
        assert result.returncode == 0
        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert "screenshot" in data
