"""Tests for vlm_detector.py — all API calls are mocked."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from vlm_detector import (
    VLMDetector,
    _load_pages,
    eval_corpus,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_image(tmp_path: Path) -> Path:
    """Tiny valid PNG (1x1 white pixel)."""
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"  # signature
        b"\x00\x00\x00\rIHDR"  # IHDR chunk length + type
        b"\x00\x00\x00\x01"  # width=1
        b"\x00\x00\x00\x01"  # height=1
        b"\x08\x02\x00\x00\x00"  # bit_depth=8 color_type=2 (RGB)
        b"\x90wS\xde"  # crc
        b"\x00\x00\x00\x0cIDATx"  # IDAT length+type+zlib header
        b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"  # compressed data
        b"\x00\x00\x00\x00IEND\xaeB`\x82"  # IEND
    )
    p = tmp_path / "screen.png"
    p.write_bytes(png_bytes)
    return p


def _make_detector(pages: list[str] | None = None) -> VLMDetector:
    """Return a VLMDetector with a mocked OpenAI client (no server required)."""
    d = VLMDetector.__new__(VLMDetector)
    d._client = MagicMock()
    d._model = "Qwen/Qwen2.5-VL-7B-Instruct"
    d._pages = pages if pages is not None else ["page_main", "page_guild", "page_shop"]
    return d


def _set_response(detector: VLMDetector, text: str) -> None:
    """Wire the mock client to return *text* as the assistant reply."""
    choice = MagicMock()
    choice.message.content = text
    detector._client.chat.completions.create.return_value = MagicMock(choices=[choice])


# ---------------------------------------------------------------------------
# _load_pages
# ---------------------------------------------------------------------------


class TestLoadPages:
    def test_returns_sorted_list(self, tmp_path: Path):
        g = {"states": {"page_z": {}, "page_a": {}, "page_m": {}}, "transitions": []}
        (tmp_path / "graph.json").write_text(json.dumps(g))
        pages = _load_pages(tmp_path / "graph.json")
        assert pages == sorted(pages)
        assert "page_a" in pages

    def test_missing_file_returns_empty(self, tmp_path: Path):
        pages = _load_pages(tmp_path / "nonexistent.json")
        assert pages == []

    def test_no_states_key(self, tmp_path: Path):
        (tmp_path / "graph.json").write_text(json.dumps({}))
        assert _load_pages(tmp_path / "graph.json") == []


# ---------------------------------------------------------------------------
# VLMDetector.detect_page
# ---------------------------------------------------------------------------


class TestDetectPage:
    def test_exact_match(self, sample_image: Path):
        d = _make_detector(["page_main", "page_guild"])
        _set_response(d, "page_main")
        page, raw = d.detect_page(sample_image)
        assert page == "page_main"
        assert raw == "page_main"

    def test_model_adds_trailing_dot(self, sample_image: Path):
        """Model sometimes returns 'page_main.' — strip punctuation."""
        d = _make_detector(["page_main", "page_guild"])
        _set_response(d, "page_main.")
        page, _ = d.detect_page(sample_image)
        assert page == "page_main"

    def test_model_adds_extra_words(self, sample_image: Path):
        """'The screen shows page_guild' — fuzzy fallback."""
        d = _make_detector(["page_main", "page_guild"])
        _set_response(d, "The screen shows page_guild")
        page, _ = d.detect_page(sample_image)
        assert page == "page_guild"

    def test_unknown_when_no_match(self, sample_image: Path):
        d = _make_detector(["page_main", "page_guild"])
        _set_response(d, "loading_screen")
        page, _ = d.detect_page(sample_image)
        assert page == "page_unknown"

    def test_page_unknown_passthrough(self, sample_image: Path):
        """Model may reply page_unknown directly."""
        d = _make_detector(["page_main"])
        _set_response(d, "page_unknown")
        page, _ = d.detect_page(sample_image)
        assert page == "page_unknown"

    def test_api_called_once(self, sample_image: Path):
        d = _make_detector()
        _set_response(d, "page_main")
        d.detect_page(sample_image)
        d._client.chat.completions.create.assert_called_once()

    def test_prompt_contains_all_pages(self, sample_image: Path):
        pages = ["page_main", "page_guild", "page_shop"]
        d = _make_detector(pages)
        _set_response(d, "page_main")
        d.detect_page(sample_image)
        call_kwargs = d._client.chat.completions.create.call_args[1]
        user_content = call_kwargs["messages"][1]["content"]
        user_text = next(c["text"] for c in user_content if c["type"] == "text")
        for p in pages:
            assert p in user_text

    def test_image_sent_as_base64(self, sample_image: Path):
        d = _make_detector()
        _set_response(d, "page_main")
        d.detect_page(sample_image)
        call_kwargs = d._client.chat.completions.create.call_args[1]
        user_content = call_kwargs["messages"][1]["content"]
        img_msg = next(c for c in user_content if c["type"] == "image_url")
        assert img_msg["image_url"]["url"].startswith("data:image/png;base64,")

    def test_temperature_zero(self, sample_image: Path):
        d = _make_detector()
        _set_response(d, "page_main")
        d.detect_page(sample_image)
        kwargs = d._client.chat.completions.create.call_args[1]
        assert kwargs["temperature"] == 0.0


# ---------------------------------------------------------------------------
# VLMDetector.locate_element
# ---------------------------------------------------------------------------


class TestLocateElement:
    def test_returns_coordinates(self, sample_image: Path):
        d = _make_detector()
        _set_response(d, "640,360")
        result = d.locate_element(sample_image, "back button")
        assert result == (640, 360)

    def test_coordinates_with_spaces(self, sample_image: Path):
        d = _make_detector()
        _set_response(d, "640, 360")
        assert d.locate_element(sample_image, "ok button") == (640, 360)

    def test_not_visible_returns_none(self, sample_image: Path):
        d = _make_detector()
        _set_response(d, "not_visible")
        assert d.locate_element(sample_image, "nonexistent") is None

    def test_not_visible_case_insensitive(self, sample_image: Path):
        d = _make_detector()
        _set_response(d, "Not_Visible")
        assert d.locate_element(sample_image, "nonexistent") is None

    def test_noisy_response_still_parsed(self, sample_image: Path):
        """Model may wrap coords in prose."""
        d = _make_detector()
        _set_response(d, "The button is at 128,720 in the bottom area.")
        result = d.locate_element(sample_image, "back")
        assert result == (128, 720)

    def test_unparseable_returns_none(self, sample_image: Path):
        d = _make_detector()
        _set_response(d, "I cannot determine from this image.")
        assert d.locate_element(sample_image, "back") is None

    def test_description_in_prompt(self, sample_image: Path):
        d = _make_detector()
        _set_response(d, "not_visible")
        d.locate_element(sample_image, "commission tab")
        kwargs = d._client.chat.completions.create.call_args[1]
        user_content = kwargs["messages"][1]["content"]
        user_text = next(c["text"] for c in user_content if c["type"] == "text")
        assert "commission tab" in user_text


# ---------------------------------------------------------------------------
# eval_corpus
# ---------------------------------------------------------------------------


class TestEvalCorpus:
    def _make_index(self, tmp_path: Path, records: list[dict]) -> Path:
        raw_dir = tmp_path / "raw_stream"
        raw_dir.mkdir()
        for rec in records:
            (raw_dir / rec["path"]).touch()
        (raw_dir / "index.jsonl").write_text("\n".join(json.dumps(r) for r in records))
        return raw_dir

    def test_perfect_accuracy(self, tmp_path: Path):
        records = [
            {"ts": 1, "path": "a.png", "alas_page": "page_main", "confidence": "arrive"},
            {"ts": 2, "path": "b.png", "alas_page": "page_guild", "confidence": "arrive"},
        ]
        raw_dir = self._make_index(tmp_path, records)
        d = _make_detector()

        results_iter = iter([("page_main", "page_main"), ("page_guild", "page_guild")])
        d.detect_page = lambda p: next(results_iter)

        result = eval_corpus(d, raw_stream_dir=raw_dir)
        assert result["accuracy"] == 1.0
        assert result["correct"] == 2

    def test_partial_accuracy(self, tmp_path: Path):
        records = [
            {"ts": 1, "path": "a.png", "alas_page": "page_main", "confidence": "arrive"},
            {"ts": 2, "path": "b.png", "alas_page": "page_guild", "confidence": "arrive"},
        ]
        raw_dir = self._make_index(tmp_path, records)
        d = _make_detector()

        results_iter = iter([("page_main", "page_main"), ("page_shop", "page_shop")])
        d.detect_page = lambda p: next(results_iter)

        result = eval_corpus(d, raw_stream_dir=raw_dir)
        assert result["accuracy"] == 0.5
        assert len(result["wrong_samples"]) == 1

    def test_filters_non_arrive(self, tmp_path: Path):
        records = [
            {"ts": 1, "path": "a.png", "alas_page": "page_main", "confidence": "arrive"},
            {"ts": 2, "path": "b.png", "alas_page": "page_main", "confidence": "switch"},
        ]
        raw_dir = self._make_index(tmp_path, records)
        d = _make_detector()
        d.detect_page = lambda p: ("page_main", "page_main")

        result = eval_corpus(d, raw_stream_dir=raw_dir)
        assert result["total"] == 1  # switch frame excluded

    def test_skips_unknown_labels(self, tmp_path: Path):
        records = [
            {"ts": 1, "path": "a.png", "alas_page": "unknown", "confidence": "arrive"},
            {"ts": 2, "path": "b.png", "alas_page": "page_main", "confidence": "arrive"},
        ]
        raw_dir = self._make_index(tmp_path, records)
        d = _make_detector()
        d.detect_page = lambda p: ("page_main", "page_main")

        result = eval_corpus(d, raw_stream_dir=raw_dir)
        assert result["total"] == 1

    def test_missing_index_raises(self, tmp_path: Path):
        d = _make_detector()
        with pytest.raises(FileNotFoundError):
            eval_corpus(d, raw_stream_dir=tmp_path / "nonexistent")

    def test_max_samples_respected(self, tmp_path: Path):
        records = [{"ts": i, "path": f"{i}.png", "alas_page": "page_main", "confidence": "arrive"} for i in range(50)]
        raw_dir = self._make_index(tmp_path, records)
        d = _make_detector()
        d.detect_page = lambda p: ("page_main", "page_main")

        result = eval_corpus(d, raw_stream_dir=raw_dir, max_samples=10)
        assert result["total"] == 10
