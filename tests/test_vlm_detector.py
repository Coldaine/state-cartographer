"""Smoke tests for vlm_detector — corpus labeling and adjudication tool.

These tests exercise the detector's interface without a live VLM endpoint.
They do not make network calls; they use a mock VLMClient.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

import vlm_detector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(return_value: dict) -> vlm_detector.VLMClient:
    """Return a VLMClient whose complete() always returns *return_value*."""
    client = MagicMock(spec=vlm_detector.VLMClient)
    client.complete.return_value = return_value
    return client


def _make_image(tmp_path: Path, name: str = "frame.png") -> Path:
    img = tmp_path / name
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
    return img


# ---------------------------------------------------------------------------
# detect_page
# ---------------------------------------------------------------------------


class TestDetectPage:
    def test_returns_primary_label(self, tmp_path: Path):
        img = _make_image(tmp_path)
        primary = {"label": "page_main", "confidence": 0.95, "rationale": "main screen visible"}
        client = _make_client(primary)

        result = vlm_detector.detect_page(img, ["page_main", "page_commission"], client=client)

        assert result["mode"] == "page-detect"
        assert result["primary"]["label"] == "page_main"
        assert result["candidate_labels"] == ["page_main", "page_commission"]

    def test_raises_on_empty_candidate_labels(self, tmp_path: Path):
        img = _make_image(tmp_path)
        with pytest.raises(ValueError, match="candidate_labels"):
            vlm_detector.detect_page(img, [], client=_make_client({}))

    def test_includes_secondary_and_agreement_when_secondary_client_given(self, tmp_path: Path):
        img = _make_image(tmp_path)
        primary = {"label": "page_main", "confidence": 0.9}
        secondary = {"label": "page_main", "confidence": 0.85}

        result = vlm_detector.detect_page(
            img,
            ["page_main"],
            client=_make_client(primary),
            secondary_client=_make_client(secondary),
        )

        assert result["secondary"]["label"] == "page_main"
        assert result["agreement"] is True

    def test_agreement_false_on_label_mismatch(self, tmp_path: Path):
        img = _make_image(tmp_path)

        result = vlm_detector.detect_page(
            img,
            ["page_main", "page_commission"],
            client=_make_client({"label": "page_main"}),
            secondary_client=_make_client({"label": "page_commission"}),
        )

        assert result["agreement"] is False

    def test_image_count_reflects_neighbors(self, tmp_path: Path):
        img = _make_image(tmp_path, "primary.png")
        neighbor = _make_image(tmp_path, "neighbor.png")
        client = _make_client({"label": "page_main", "confidence": 0.8})

        result = vlm_detector.detect_page(
            img, ["page_main"], neighbor_paths=[neighbor], client=client
        )

        assert result["image_count"] == 2


# ---------------------------------------------------------------------------
# locate_element
# ---------------------------------------------------------------------------


class TestLocateElement:
    def test_returns_result_with_bbox(self, tmp_path: Path):
        img = _make_image(tmp_path)
        response = {"found": True, "confidence": 0.9, "bbox": [100, 200, 300, 400]}
        client = _make_client(response)

        result = vlm_detector.locate_element(img, "back button", client=client)

        assert result["mode"] == "element-locate"
        assert result["result"]["found"] is True
        assert result["result"]["bbox"] == [100, 200, 300, 400]

    def test_returns_not_found(self, tmp_path: Path):
        img = _make_image(tmp_path)
        client = _make_client({"found": False, "bbox": None, "confidence": 0.1})

        result = vlm_detector.locate_element(img, "nonexistent element", client=client)

        assert result["result"]["found"] is False
        assert result["result"]["bbox"] is None

    def test_raises_on_empty_target(self, tmp_path: Path):
        img = _make_image(tmp_path)
        with pytest.raises(ValueError, match="target"):
            vlm_detector.locate_element(img, "   ", client=_make_client({}))


# ---------------------------------------------------------------------------
# _parse_json_response
# ---------------------------------------------------------------------------


class TestParseJsonResponse:
    def test_parses_plain_json(self):
        text = '{"label": "page_main", "confidence": 0.9}'
        result = vlm_detector._parse_json_response(text)
        assert result["label"] == "page_main"

    def test_strips_code_fence(self):
        text = "```json\n{\"label\": \"page_dorm\"}\n```"
        result = vlm_detector._parse_json_response(text)
        assert result["label"] == "page_dorm"


# ---------------------------------------------------------------------------
# _extract_message_text
# ---------------------------------------------------------------------------


class TestExtractMessageText:
    def test_extracts_string_content(self):
        payload = {"choices": [{"message": {"content": "hello"}}]}
        assert vlm_detector._extract_message_text(payload) == "hello"

    def test_raises_on_empty_choices(self):
        with pytest.raises(ValueError):
            vlm_detector._extract_message_text({"choices": []})
