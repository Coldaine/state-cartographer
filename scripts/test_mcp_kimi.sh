#!/usr/bin/env bash
# test_mcp_kimi.sh — Test MCP servers via Kimi CLI
# Usage: bash scripts/test_mcp_kimi.sh [device_serial]
#
# Uses --mcp-config-file to load the project .mcp.json and --print for
# non-interactive (headless) mode. Tests scrcpy-mcp, mobile-mcp, and maa-mcp.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MCP_CONFIG="$REPO_ROOT/.mcp.json"
DEVICE="${1:-0323218118133}"

echo "=== Kimi MCP Test ==="
echo "Device: $DEVICE"
echo "MCP config: $MCP_CONFIG"
echo "Working dir: $REPO_ROOT"
cd "$REPO_ROOT"

KIMI_BASE_ARGS=(
  --mcp-config-file "$MCP_CONFIG"
  --print
  --output-format text
)

echo ""
echo "--- Test 1: scrcpy-mcp — list devices ---"
kimi "${KIMI_BASE_ARGS[@]}" \
  -p "Use the scrcpy-mcp device_list tool to list all connected ADB devices. Report results."

echo ""
echo "--- Test 2: scrcpy-mcp — screenshot ---"
kimi "${KIMI_BASE_ARGS[@]}" \
  -p "Use scrcpy-mcp to take a screenshot of device serial ${DEVICE}. Describe what is visible on screen in one sentence."

echo ""
echo "--- Test 3: scrcpy-mcp — device info ---"
kimi "${KIMI_BASE_ARGS[@]}" \
  -p "Use scrcpy-mcp device_info to get hardware info for device ${DEVICE}. Report the model name and Android API level."

echo ""
echo "--- Test 4: mobile-mcp — list devices ---"
kimi "${KIMI_BASE_ARGS[@]}" \
  -p "Use the mobile-mcp mobile_list_available_devices tool to list connected devices. Report the result."

echo ""
echo "--- Test 5: maa-mcp — find ADB devices ---"
kimi "${KIMI_BASE_ARGS[@]}" \
  -p "Use the maa-mcp find_adb_device_list tool to discover ADB devices. Report what is found."

echo ""
echo "=== Kimi MCP Test Complete ==="
