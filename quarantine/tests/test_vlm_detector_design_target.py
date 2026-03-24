import json
from pathlib import Path

import pytest

from scripts import vlm_detector


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    image = tmp_path / "sample.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return image


def test_detect_page_posts_openai_compatible_payload(monkeypatch, sample_image):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json_module.dumps(
                                {
                                    "label": "commission_list",
                                    "confidence": 0.82,
                                    "rationale": "Tab layout matches the commission list.",
                                    "uncertainty_flags": [],
                                    "recommended_followups": [],
                                }
                            )
                        }
                    }
                ]
            }
        )

    json_module = json
    monkeypatch.setattr(vlm_detector.requests, "post", fake_post)

    client = vlm_detector.VLMClient(base_url="http://localhost:9999/v1", model="test-model")
    result = vlm_detector.detect_page(
        sample_image,
        ["commission_list", "popup_confirm"],
        task_context="commission",
        client=client,
    )

    assert result["primary"]["label"] == "commission_list"
    assert captured["url"] == "http://localhost:9999/v1/chat/completions"
    assert captured["json"]["model"] == "test-model"
    assert captured["json"]["response_format"] == {"type": "json_object"}
    user_message = captured["json"]["messages"][1]["content"]
    assert user_message[0]["type"] == "text"
    assert "commission_list" in user_message[0]["text"]
    assert user_message[1]["type"] == "image_url"


def test_detect_page_supports_secondary_adjudication(monkeypatch, sample_image):
    payloads = iter(
        [
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "label": "commission_list",
                                    "confidence": 0.91,
                                    "rationale": "Primary call",
                                    "uncertainty_flags": [],
                                    "recommended_followups": [],
                                }
                            )
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "label": "popup_confirm",
                                    "confidence": 0.77,
                                    "rationale": "Secondary call",
                                    "uncertainty_flags": ["overlay"],
                                    "recommended_followups": ["inspect neighboring frame"],
                                }
                            )
                        }
                    }
                ]
            },
        ]
    )

    def fake_post(url, headers, json, timeout):
        return FakeResponse(next(payloads))

    monkeypatch.setattr(vlm_detector.requests, "post", fake_post)

    primary = vlm_detector.VLMClient(base_url="http://primary/v1", model="primary")
    secondary = vlm_detector.VLMClient(base_url="http://secondary/v1", model="secondary")
    result = vlm_detector.detect_page(
        sample_image,
        ["commission_list", "popup_confirm"],
        client=primary,
        secondary_client=secondary,
    )

    assert result["primary"]["label"] == "commission_list"
    assert result["secondary"]["label"] == "popup_confirm"
    assert result["agreement"] is False


def test_detect_page_includes_neighbor_and_exemplar_images(monkeypatch, tmp_path: Path):
    image = tmp_path / "frame0.png"
    neighbor = tmp_path / "frame1.png"
    exemplar = tmp_path / "example.png"
    for path in (image, neighbor, exemplar):
        path.write_bytes(b"\x89PNG\r\n\x1a\nfake")

    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["messages"] = json["messages"]
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json_module.dumps(
                                {
                                    "label": "unknown",
                                    "confidence": 0.4,
                                    "rationale": "Needs review.",
                                    "uncertainty_flags": ["ambiguous"],
                                    "recommended_followups": ["check sequence"],
                                }
                            )
                        }
                    }
                ]
            }
        )

    json_module = json
    monkeypatch.setattr(vlm_detector.requests, "post", fake_post)

    result = vlm_detector.detect_page(
        image,
        ["unknown"],
        neighbor_paths=[neighbor],
        exemplar_paths=[exemplar],
    )

    content = captured["messages"][1]["content"]
    image_parts = [part for part in content if part["type"] == "image_url"]
    assert len(image_parts) == 3
    assert result["image_count"] == 3


def test_locate_element_returns_bbox_result(monkeypatch, sample_image):
    def fake_post(url, headers, json, timeout):
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "found": True,
                                    "confidence": 0.88,
                                    "rationale": "Button is visible in the lower-right region.",
                                    "bbox": [100, 200, 180, 240],
                                    "recommended_followups": [],
                                }
                            )
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(vlm_detector.requests, "post", fake_post)

    result = vlm_detector.locate_element(sample_image, "collect reward button", task_context="commission")

    assert result["mode"] == "element-locate"
    assert result["result"]["found"] is True
    assert result["result"]["bbox"] == [100, 200, 180, 240]
