#!/usr/bin/env bash
# test_mcp_gemini.sh — Test MCP servers via Gemini CLI
# Usage: bash scripts/test_mcp_gemini.sh [device_serial]
#
# Registers scrcpy-mcp with Gemini (project scope) then drives it non-interactively
# with -y (YOLO mode, auto-approves all tool calls).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEVICE="${1:-0323218118133}"

SCRCPY_SERVER_PATH='C:\Users\pmacl\AppData\Local\Microsoft\WinGet\Packages\Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe\scrcpy-win64-v3.3.4\scrcpy-server'

echo "=== Gemini MCP Test ==="
echo "Device: $DEVICE"
echo "Working dir: $REPO_ROOT"
cd "$REPO_ROOT"

# Register scrcpy-mcp with Gemini (idempotent — add only if not present)
if ! gemini mcp list 2>/dev/null | grep -q "scrcpy-mcp"; then
  echo "Registering scrcpy-mcp with Gemini (project scope)..."
  gemini mcp add scrcpy-mcp npx \
    --scope project \
    --trust \
    -e "SCRCPY_SERVER_PATH=${SCRCPY_SERVER_PATH}" \
    -- -y scrcpy-mcp
  echo "Registered."
else
  echo "scrcpy-mcp already registered."
fi

echo ""
echo "--- Test 1: List devices ---"
gemini \
  -p "Use the scrcpy-mcp device_list tool to list available ADB devices. Report the result." \
  -y \
  --allowed-mcp-server-names scrcpy-mcp \
  --output-format text

echo ""
echo "--- Test 2: Screenshot ---"
gemini \
  -p "Use scrcpy-mcp to take a screenshot of device serial ${DEVICE}. Describe what you see on screen in one sentence." \
  -y \
  --allowed-mcp-server-names scrcpy-mcp \
  --output-format text

echo ""
echo "--- Test 3: Device info ---"
gemini \
  -p "Use scrcpy-mcp device_info to get info for device ${DEVICE}. Report the model, Android version, and screen resolution." \
  -y \
  --allowed-mcp-server-names scrcpy-mcp \
  --output-format text

echo ""
echo "=== Gemini MCP Test Complete ==="
