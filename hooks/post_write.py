#!/usr/bin/env python3
"""Post-write hook for state-cartographer.

Runs after any Write tool invocation. Performs two actions:
1. If a graph.json file was written and a validator exists, validate it.
2. If a .py file in scripts/ was written, run ruff format/check on it.

Receives hook input JSON on stdin. Outputs structured JSON on stdout.
Exit 0 = success. Validation and formatting issues are reported as warnings.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path:
        return 0

    path = Path(file_path)

    # Auto-validate graph.json files after write when a validator is available.
    if path.name == "graph.json" and path.exists():
        plugin_root = Path(__file__).parent.parent
        validator = plugin_root / "scripts" / "schema_validator.py"
        if validator.exists():
            result = subprocess.run(
                [sys.executable, str(validator), str(path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                print(
                    json.dumps(
                        {
                            "additionalContext": f"Graph validation warning: {result.stderr.strip() or result.stdout.strip()}"
                        }
                    ),
                    flush=True,
                )
        else:
            print(
                json.dumps(
                    {
                        "additionalContext": (
                            "Graph validation warning: schema validator is not present in this repo snapshot; "
                            "skipping automatic validation."
                        )
                    }
                ),
                flush=True,
            )

    # Auto-format Python files in scripts/ after write
    if path.suffix == ".py" and "scripts" in path.parts:
        format_result = subprocess.run(
            [sys.executable, "-m", "ruff", "format", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        check_result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--fix", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )

        warning = format_result.stderr.strip() or check_result.stderr.strip()
        if format_result.returncode != 0 or check_result.returncode != 0:
            print(
                json.dumps({"additionalContext": f"Ruff warning: {warning or 'ruff formatting failed'}"}),
                flush=True,
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
