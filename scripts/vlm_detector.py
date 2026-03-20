"""vlm_detector.py — VLM-based game state detection for Azur Lane.

Replaces the pixel-anchor approach in locate.py with a call to a locally-served
vision-language model.  Designed for Qwen2.5-VL-7B-Instruct served via vLLM,
which fits in ~18 GB VRAM and exposes an OpenAI-compatible API at localhost:8000.

Serving the model (one-time setup):
    pip install vllm
    vllm serve Qwen/Qwen2.5-VL-7B-Instruct \\
        --limit-mm-per-prompt image=1 \\
        --max-model-len 8192

Capabilities:
    detect_page(image)            -> (page_id, raw_response)
    locate_element(image, prompt) -> (x, y) | None

CLI:
    uv run python scripts/vlm_detector.py --screenshot data/raw_stream/foo.png
    uv run python scripts/vlm_detector.py --screenshot foo.png --locate "back button"
    uv run python scripts/vlm_detector.py --eval-corpus   # score against index.jsonl
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
GRAPH_PATH = REPO_ROOT / "examples" / "azur-lane" / "graph.json"
RAW_STREAM = REPO_ROOT / "data" / "raw_stream"

# vLLM endpoint (Qwen3.5-9B-AWQ on RTX 5090, port 18900)
DEFAULT_BASE_URL = "http://localhost:18900/v1"
DEFAULT_MODEL = "QuantTrio/Qwen3.5-9B-AWQ"

# ---------------------------------------------------------------------------
# Page list (loaded from graph.json so it stays in sync automatically)
# ---------------------------------------------------------------------------


def _load_pages(graph_path: Path = GRAPH_PATH) -> list[str]:
    if not graph_path.exists():
        return []
    g = json.loads(graph_path.read_text(encoding="utf-8"))
    return sorted(g.get("states", {}).keys())


KNOWN_PAGES: list[str] = _load_pages()

_SYSTEM_PROMPT = """\
You are analyzing screenshots from the mobile game Azur Lane (English version, 1280x720).
Answer concisely and precisely. Do not explain."""

_PAGE_DETECT_TMPL = """\
Which of the following Azur Lane screens is shown?

{pages}

Reply with ONLY the exact identifier from the list above (e.g. page_main).
If the screen matches none of them, reply: page_unknown"""

_LOCATE_TMPL = """\
In this 1280x720 Azur Lane screenshot, find: {description}

Reply with ONLY the pixel coordinates in the format:  x,y
If the element is not visible, reply: not_visible"""


# ---------------------------------------------------------------------------
# VLMDetector
# ---------------------------------------------------------------------------


class VLMDetector:
    """Wraps a vLLM-served Qwen2.5-VL endpoint for state detection and grounding."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        pages: list[str] | None = None,
        timeout: float = 30.0,
    ):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package required: uv add openai") from exc

        self._client = OpenAI(base_url=base_url, api_key="not-needed", timeout=timeout)
        self._model = model
        self._pages = pages if pages is not None else KNOWN_PAGES

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _encode_image(path: Path) -> str:
        """Base64-encode an image file for the vision API."""
        return base64.b64encode(path.read_bytes()).decode("utf-8")

    def _call(self, image_path: Path, user_text: str, max_tokens: int = 64) -> str:
        """Make one vision API call and return the raw text response."""
        b64 = self._encode_image(image_path)
        ext = image_path.suffix.lstrip(".").lower()
        mime = "image/png" if ext == "png" else f"image/{ext}"

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                        {"type": "text", "text": user_text},
                    ],
                },
            ],
            max_tokens=max_tokens,
            temperature=0.0,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        return response.choices[0].message.content.strip()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_page(self, image_path: Path) -> tuple[str, str]:
        """Identify the current game page from a screenshot.

        Returns (page_id, raw_response).
        page_id is one of KNOWN_PAGES, or "page_unknown" if unrecognised.
        """
        user_text = _PAGE_DETECT_TMPL.format(pages="\n".join(self._pages))
        raw = self._call(image_path, user_text, max_tokens=32)

        # Normalise: strip punctuation, match against known pages
        candidate = raw.strip().rstrip(".").lower()
        if candidate in self._pages:
            return candidate, raw
        # Fuzzy: maybe model added extra words
        for p in self._pages:
            if p in candidate:
                return p, raw
        return "page_unknown", raw

    def locate_element(self, image_path: Path, description: str) -> tuple[int, int] | None:
        """Return pixel (x, y) of a described UI element, or None if not found."""
        user_text = _LOCATE_TMPL.format(description=description)
        raw = self._call(image_path, user_text, max_tokens=32)

        if "not_visible" in raw.lower():
            return None
        # Parse "x,y" possibly surrounded by noise
        m = re.search(r"\b(\d{1,4})\s*,\s*(\d{1,4})\b", raw)
        if m:
            return int(m.group(1)), int(m.group(2))
        return None


# ---------------------------------------------------------------------------
# Eval: score VLM against the labeled index.jsonl
# ---------------------------------------------------------------------------


def eval_corpus(
    detector: VLMDetector,
    raw_stream_dir: Path = RAW_STREAM,
    confidence_filter: str = "arrive",
    max_samples: int = 200,
) -> dict[str, Any]:
    """Score VLM page detection against the ALAS-labeled index.jsonl.

    Only evaluates frames with confidence == arrive (ground truth from ALAS
    template matching) and skips page_unknown labels.
    """
    index = raw_stream_dir / "index.jsonl"
    if not index.exists():
        raise FileNotFoundError(f"No index.jsonl at {index} — run label_raw_stream.py first")

    records = [json.loads(ln) for ln in index.read_text().splitlines() if ln.strip()]
    if confidence_filter:
        records = [r for r in records if r.get("confidence") == confidence_filter]
    records = [r for r in records if r.get("alas_page", "unknown") != "unknown"]
    records = records[:max_samples]

    correct = 0
    wrong: list[dict] = []
    for rec in records:
        img = raw_stream_dir / rec["path"]
        if not img.exists():
            continue
        got, raw = detector.detect_page(img)
        if got == rec["alas_page"]:
            correct += 1
        else:
            wrong.append({"path": rec["path"], "expected": rec["alas_page"], "got": got, "raw": raw})

    total = len(records)
    return {
        "total": total,
        "correct": correct,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "wrong_samples": wrong[:10],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VLM-based Azur Lane state detector")
    parser.add_argument("--screenshot", type=Path, help="Path to a PNG screenshot")
    parser.add_argument("--locate", type=str, help="Describe a UI element to find its (x,y)")
    parser.add_argument("--eval-corpus", action="store_true", help="Score VLM against labeled index.jsonl")
    parser.add_argument("--max-eval-samples", type=int, default=100)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args(argv)

    try:
        detector = VLMDetector(base_url=args.base_url, model=args.model)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if args.eval_corpus:
        print("Evaluating against labeled corpus (arrive-confidence only)...")
        try:
            results = eval_corpus(detector, max_samples=args.max_eval_samples)
        except (FileNotFoundError, Exception) as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
        print(f"Accuracy: {results['correct']}/{results['total']} = {results['accuracy'] * 100:.1f}%")
        if results["wrong_samples"]:
            print("Wrong samples:")
            for w in results["wrong_samples"]:
                print(f"  {w['path']}: expected={w['expected']} got={w['got']!r}")
        return 0

    if not args.screenshot:
        parser.print_help()
        return 1

    screenshot = args.screenshot
    if not screenshot.exists():
        print(f"ERROR: Screenshot not found: {screenshot}", file=sys.stderr)
        return 1

    if args.locate:
        coords = detector.locate_element(screenshot, args.locate)
        if coords:
            x, y = coords
            print(f"{x},{y}")
        else:
            print("not_visible")
        return 0

    page, raw = detector.detect_page(screenshot)
    print(f"page: {page}")
    print(f"raw:  {raw}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
