#!/usr/bin/env python3
"""Thin Kimi CLI wrapper for cheap screenshot-first review.

This is intentionally narrow:

- visible-only description
- optional closed-set label selection
- optional neighboring frames for context

It is for cheap first-pass review and disagreement surfacing, not for trusted
ground truth generation.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

VISIBLE_ONLY_PROMPT = """Inspect the provided screenshot set.

Return valid JSON with exactly these keys:
- visible_text: list of short strings copied or paraphrased from visible UI text
- visible_regions: list of short strings naming major visible panels, cards, buttons, tabs, or overlays
- best_label: string or null
- confidence: float from 0.0 to 1.0
- ambiguity_notes: list of short strings

Rules:
- use only what is visibly present in the images
- do not infer the next destination, intended task, or hidden state from workflow expectations
- if a label set is provided, choose only from that set or return null
- evidence first, label second

Task context: {task_context}
Allowed labels: {allowed_labels}
"""


def build_prompt(
    image_paths: list[Path],
    *,
    task_context: str,
    allowed_labels: list[str],
) -> str:
    image_list = "\n".join(f"- {path}" for path in image_paths)
    labels_text = json.dumps(allowed_labels) if allowed_labels else "null"
    return (
        VISIBLE_ONLY_PROMPT.format(task_context=task_context, allowed_labels=labels_text) + "\nImages:\n" + image_list
    )


def run_kimi(prompt: str, *, workdir: Path) -> str:
    command = [
        "kimi",
        "--print",
        "--final-message-only",
        "-w",
        str(workdir),
        "-p",
        prompt,
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cheap Kimi-backed screenshot review helper.")
    parser.add_argument("image", help="Primary screenshot path.")
    parser.add_argument("--neighbor-image", action="append", default=[], help="Additional nearby frame.")
    parser.add_argument("--label", action="append", default=[], help="Closed-set allowed label.")
    parser.add_argument("--task-context", default="unknown", help="Optional task or workflow context.")
    parser.add_argument(
        "--workdir",
        default=".",
        help="Working directory for the Kimi CLI session. Default: current directory.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    image_paths = [Path(args.image), *(Path(path) for path in args.neighbor_image)]
    prompt = build_prompt(
        image_paths,
        task_context=args.task_context,
        allowed_labels=list(args.label),
    )
    output = run_kimi(prompt, workdir=Path(args.workdir).resolve())
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
