"""Offline VLM labeling and adjudication helpers.

This module is intentionally narrow.

It is kept to support corpus labeling and offline analysis around the ALAS log
+ screenshot workflow. It is not trusted runtime truth and should not be used
as a live control-plane primitive.

Prompt specifications live under:

- docs/vlm/VLM-overview.md
- docs/vlm/VLM-task-contracts.md
- docs/vlm/VLM-prompts.md

Augmentation targets for the rebuild:

- multi-image context should become the default, not the exception
- task context should be passed when known
- retrieved exemplars should be supported
- secondary model adjudication should be easy to enable for offline review
- graph-derived labels are no longer assumed to be the source of truth
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
from pathlib import Path
from typing import Any

import requests

DEFAULT_BASE_URL = os.getenv("SC_VLM_BASE_URL", "http://localhost:18900/v1")
DEFAULT_MODEL = os.getenv("SC_VLM_MODEL", "local-vlm")

SYSTEM_PROMPT = """You are a strict screenshot labeling assistant.

Use only the information provided in the request.
Prefer explicit uncertainty over confident guessing.
Return JSON that matches the requested schema exactly.
"""

PAGE_DETECT_PROMPT = """Label the screenshot set.

Task context: {task_context}
Candidate labels: {candidate_labels}

Return JSON with:
- label: the best candidate label
- confidence: float from 0.0 to 1.0
- rationale: short explanation grounded in visible evidence
- uncertainty_flags: list of short strings
- recommended_followups: list of short strings
"""

ELEMENT_LOCATE_PROMPT = """Locate the requested UI element in the screenshot set.

Target element: {target}
Task context: {task_context}

Return JSON with:
- found: boolean
- confidence: float from 0.0 to 1.0
- rationale: short explanation grounded in visible evidence
- bbox: [x1, y1, x2, y2] or null
- recommended_followups: list of short strings
"""


def _image_to_data_url(image_path: str | Path) -> str:
    path = Path(image_path)
    mime, _ = mimetypes.guess_type(path.name)
    mime = mime or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _normalize_image_paths(
    image_path: str | Path,
    neighbor_paths: list[str | Path] | None = None,
    exemplar_paths: list[str | Path] | None = None,
) -> list[Path]:
    ordered: list[Path] = [Path(image_path)]
    for group in (neighbor_paths or [], exemplar_paths or []):
        for p in group:
            candidate = Path(p)
            if candidate not in ordered:
                ordered.append(candidate)
    return ordered


def _build_messages(system_prompt: str, prompt: str, image_paths: list[Path]) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for image_path in image_paths:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": _image_to_data_url(image_path),
                },
            }
        )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content},
    ]


def _extract_message_text(payload: dict[str, Any]) -> str:
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
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
    return json.loads(stripped)


class VLMClient:
    """Small OpenAI-compatible client for offline labeling workflows."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, model: str = DEFAULT_MODEL, timeout_s: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    def complete(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
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


def detect_page(
    image_path: str | Path,
    candidate_labels: list[str],
    *,
    task_context: str = "unknown",
    neighbor_paths: list[str | Path] | None = None,
    exemplar_paths: list[str | Path] | None = None,
    client: VLMClient | None = None,
    secondary_client: VLMClient | None = None,
) -> dict[str, Any]:
    """Classify screenshots into one of the provided labels.

    This is intentionally an offline helper.
    The caller is expected to decide what labels are meaningful for the current
    corpus pass. No graph file is loaded implicitly.
    """

    if not candidate_labels:
        raise ValueError("candidate_labels must not be empty")

    client = client or VLMClient()
    image_paths = _normalize_image_paths(image_path, neighbor_paths, exemplar_paths)
    prompt = PAGE_DETECT_PROMPT.format(
        task_context=task_context,
        candidate_labels=json.dumps(candidate_labels),
    )
    primary = client.complete(_build_messages(SYSTEM_PROMPT, prompt, image_paths))

    result: dict[str, Any] = {
        "mode": "page-detect",
        "primary": primary,
        "candidate_labels": candidate_labels,
        "task_context": task_context,
        "image_count": len(image_paths),
    }

    # Augmentation hook: offline adjudication can fan out to a second model.
    # This is for review and disagreement analysis, not runtime truth.
    if secondary_client is not None:
        secondary = secondary_client.complete(_build_messages(SYSTEM_PROMPT, prompt, image_paths))
        result["secondary"] = secondary
        result["agreement"] = primary.get("label") == secondary.get("label")

    return result


def locate_element(
    image_path: str | Path,
    target: str,
    *,
    task_context: str = "unknown",
    neighbor_paths: list[str | Path] | None = None,
    exemplar_paths: list[str | Path] | None = None,
    client: VLMClient | None = None,
) -> dict[str, Any]:
    """Locate a target element in one or more screenshots."""

    if not target.strip():
        raise ValueError("target must not be empty")

    client = client or VLMClient()
    image_paths = _normalize_image_paths(image_path, neighbor_paths, exemplar_paths)
    prompt = ELEMENT_LOCATE_PROMPT.format(target=target, task_context=task_context)
    response = client.complete(_build_messages(SYSTEM_PROMPT, prompt, image_paths))
    return {
        "mode": "element-locate",
        "target": target,
        "task_context": task_context,
        "image_count": len(image_paths),
        "result": response,
    }


def _parse_path_list(values: list[str] | None) -> list[str]:
    return list(values or [])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline VLM detector for corpus labeling and adjudication.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Primary OpenAI-compatible base URL.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Primary model name.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    detect_parser = subparsers.add_parser("detect-page", help="Classify screenshot(s) into one of the provided labels.")
    detect_parser.add_argument("image", help="Primary screenshot path.")
    detect_parser.add_argument("--label", action="append", dest="labels", required=True, help="Candidate label.")
    detect_parser.add_argument("--task-context", default="unknown", help="Optional task or workflow context.")
    detect_parser.add_argument("--neighbor-image", action="append", default=[], help="Additional nearby frame.")
    detect_parser.add_argument("--exemplar-image", action="append", default=[], help="Retrieved exemplar frame.")
    detect_parser.add_argument("--secondary-base-url", help="Optional secondary base URL for adjudication.")
    detect_parser.add_argument("--secondary-model", help="Optional secondary model for adjudication.")

    locate_parser = subparsers.add_parser("locate-element", help="Locate a target element inside screenshot(s).")
    locate_parser.add_argument("image", help="Primary screenshot path.")
    locate_parser.add_argument("--target", required=True, help="Target UI element or visual cue.")
    locate_parser.add_argument("--task-context", default="unknown", help="Optional task or workflow context.")
    locate_parser.add_argument("--neighbor-image", action="append", default=[], help="Additional nearby frame.")
    locate_parser.add_argument("--exemplar-image", action="append", default=[], help="Retrieved exemplar frame.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    client = VLMClient(base_url=args.base_url, model=args.model)

    if args.command == "detect-page":
        secondary_client = None
        if args.secondary_base_url and args.secondary_model:
            secondary_client = VLMClient(base_url=args.secondary_base_url, model=args.secondary_model)
        result = detect_page(
            args.image,
            args.labels,
            task_context=args.task_context,
            neighbor_paths=_parse_path_list(args.neighbor_image),
            exemplar_paths=_parse_path_list(args.exemplar_image),
            client=client,
            secondary_client=secondary_client,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "locate-element":
        result = locate_element(
            args.image,
            args.target,
            task_context=args.task_context,
            neighbor_paths=_parse_path_list(args.neighbor_image),
            exemplar_paths=_parse_path_list(args.exemplar_image),
            client=client,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
