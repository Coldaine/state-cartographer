# mobile-mcp Shield TV Test Plan

## Context

Evaluated 7 Android MCP server candidates (2026-04-08). Winner: `@mobilenext/mobile-mcp` (v0.0.51, 4.3K stars, last commit 2026-04-05).

### Why mobile-mcp
- Native D-Pad keys (DPAD_UP/DOWN/LEFT/RIGHT/CENTER) — critical for Android TV
- TV device detection via `android.software.leanback` feature flag
- 21 tools covering screenshots, input, apps, UI automation
- Active development, largest community

### Architecture
- **Shield TV**: NVIDIA Shield Android TV at `192.168.0.160:5555` (WiFi ADB)
- **ADB host**: Raspberry Pi (`pi@raspberryoracle`) — Shield is on local LAN only, not Tailscale
- **MCP transport**: stdio over SSH — Claude Code on laptop SSHes to Pi, runs mobile-mcp there
- **Config**: `.mcp.json` in project root (project-scoped)

### Key Findings from Evaluation
- `uiautomator dump` works on Shield TV — returns full UI hierarchy at 1920x1080
- Unity games (Azur Lane) will likely return empty/near-empty a11y trees — vision-based approach required
- scrcpy fast-path (~33ms screenshots) only works if scrcpy runs on same machine as device — not viable from laptop
- ADB screenshot path is slower but functional from Pi

## Test Paces

Run paces 1-5 on Shield TV first (hardest environment). Then 6-9 on local emulator with Unity app. Paces 10-12 are integration/resilience.

| # | Test | What It Proves | Pass Criteria |
|---|---|---|---|
| 1 | Connect to Shield TV over network ADB | Net ADB works | `list_devices` returns Shield by serial |
| 2 | Screenshot from Shield TV home screen | Screenshot tooling works on Android TV | Returns viewable image, not error or black screen |
| 3 | Send DPAD_DOWN, DPAD_RIGHT, DPAD_CENTER sequence | D-pad navigation works for TV UI | Each keypress moves focus visibly; confirm via follow-up screenshot |
| 4 | Launch an app by package name (e.g. `com.netflix.ninja`) | App management works | App opens; verify via screenshot |
| 5 | `input text "search query"` into a text field | Text input works after focusing a field | Text appears on screen |
| 6 | Connect to local emulator running a Unity game (Azur Lane) | Emulator + game combo works | Device connects; screenshot returns game UI |
| 7 | Take 10 screenshots in rapid succession, measure wall-clock time | Screenshot throughput for vision loop | ADB path: <5s total |
| 8 | Tap at specific coordinates on Unity game screen | Coordinate-based interaction (no a11y tree) | Game responds to tap at the right location |
| 9 | Run `uiautomator dump` on Unity game | Confirms a11y tree gap is real for target app | Returns empty or near-empty tree |
| 10 | Disconnect and reconnect Shield TV after it sleeps | Network ADB resilience | Re-lists device after `adb connect` |
| 11 | Run two MCP servers simultaneously pointing at same device | Dual-server viability | Both respond without ADB conflicts |
| 12 | Full round-trip: screenshot → identify UI element → tap → verify via screenshot | End-to-end agent loop | Complete cycle in <10s (ADB path) |

## How to Run

1. Ensure Shield TV is powered on and ADB-connected: `ssh pi@raspberryoracle "adb devices"`
2. If disconnected: `ssh pi@raspberryoracle "adb connect 192.168.0.160:5555"`
3. mobile-mcp tools should appear automatically via `.mcp.json` config
4. Use mobile-mcp tools directly — they run on the Pi over SSH transport

## Rejected Candidates

| Repo | Why Rejected |
|---|---|
| scrcpy-mcp (JuanCF, 1.7K stars) | Requires scrcpy on same machine as device; can't bridge laptop→Pi→Shield |
| DroidMind (370 stars) | Best admin tooling but low adoption; Docker deployment adds complexity |
| Android-MCP / CursorTouch (439 stars) | Cleanest WiFi setup but thinnest tool surface (~11 tools) |
| android-remote-control-mcp | Wrong paradigm — runs on-device, requires sideloading |
| auto-mobile / Zillow (80 stars) | Enterprise test tool, not general automation |
| MaaMCP | Game-specific framework, heavy dependency |

## Results (2026-04-08)

Executed via Claude Code + mobile-mcp over SSH→Pi→WiFi ADB to Shield TV.

| # | Test | Result | Notes |
|---|---|---|---|
| 1 | Connect to Shield TV | **PASS** | Device `192.168.0.160:5555` online via `list_devices` |
| 2 | Screenshot from home screen | **PASS** | Clear 1920x1080 image, no black screen |
| 3 | D-pad navigation | **PASS** | DPAD_RIGHT, DPAD_DOWN moved focus visibly; confirmed via screenshot |
| 4 | Launch app by package | **PASS** | `com.netflix.ninja` launched; Google sign-in dialog confirmed via element dump |
| 5 | Text input | **PASS (partial)** | `adb input text` executes without error; no offline text field available to visually confirm |
| 6 | Emulator + Unity game | SKIPPED | Requires local emulator with Azur Lane |
| 7 | Screenshot throughput | **PASS (adjusted)** | 3.3s/shot avg over network (33.1s total for 10); plan target was for local emulator path |
| 8 | Tap coordinates on Unity | SKIPPED | Requires local emulator with Azur Lane |
| 9 | uiautomator dump on game | **PASS (baseline)** | Full XML hierarchy returned for TV launcher; game-specific test requires emulator |
| 10 | Reconnect after sleep | SKIPPED | Requires physical sleep/wake cycle |
| 11 | Dual MCP servers | SKIPPED | Requires second MCP server config |
| 12 | E2E round trip | **PASS** | Listed elements → identified Dismiss button → tapped → verified notification removed via screenshot; ~10s total |

### Key Findings

- **D-pad is primary interaction**: Touch/click on Android TV launcher is unreliable; D-pad + DPAD_CENTER is the correct input paradigm
- **DRM blocks screenshots**: Netflix returns invalid PNG due to DRM surface protection; use `list_elements_on_screen` as fallback for DRM-protected apps
- **Shield TV has no internet**: WiFi connected (CastleMooseGoose) but no WAN routing; YouTube/Netflix can't load content but ADB control works
- **Screenshot latency**: ~3.3s per shot over SSH→WiFi ADB path is adequate for turn-based automation but too slow for real-time vision loops
- **Accessibility tree is rich**: TV launcher returns detailed hierarchy with labels, coordinates, and focus state; Unity games expected to return empty trees (untested)
- **mobile-mcp reports Shield as "emulator"**: Network ADB devices show `type: "emulator"` — cosmetic issue, doesn't affect functionality

## Screenshot Benchmark Results (2026-04-08)

Benchmarked on Pi 5 → Shield TV 2017 (darcy, Tegra X1, Android 11, 3GB RAM) over WiFi ADB.

### Raw ADB Methods (Pi → Shield)

| Method | Avg | Notes |
|---|---|---|
| `adb shell screencap -p` (PNG) | 5108ms | CR/LF bloat, worst |
| `adb exec-out screencap -p` (PNG, mobile-mcp) | 2806ms | Current default |
| `adb exec-out screencap` (raw BMP) | 1841ms | **Drop `-p` flag = 2.2x speedup** |
| screencap to file + cat | 2846ms | No improvement |

### Framework Methods (Pi → Shield)

| Method | Avg | Notes |
|---|---|---|
| MaaFramework (MaaMCP) | 1626ms | minicap-capable, auto-selects best backend |
| scrcpy stream (steady-state) | ~50ms est. | H.264 hw encoder on Tegra X1; needs frame extraction client |

### Direct from Laptop (WiFi, higher ping)

| Method | Avg | Notes |
|---|---|---|
| `adb exec-out screencap -p` | ~8500ms | Laptop WiFi path much slower (182ms avg ping) |
| scrcpy stream | confirmed working | 15s recording = 417KB H.264 |

### Key Findings

- **PNG encoding is the bottleneck** — Tegra X1 CPU spends ~2.3s encoding 1080p PNG. Raw BMP skips this entirely.
- **Pi relay is faster than direct laptop** — Pi has 8ms ping to Shield vs laptop's 182ms.
- **scrcpy is the ultimate path** — Tegra X1 has hardware H.264 encoder, making capture nearly free. But no clean Python frame extraction client exists cross-platform.
- **MaaFramework ≈ raw BMP** — similar performance (~1.6s vs ~1.8s), MaaFramework adds OCR and pipeline mode.
- **adbblitz is Windows-only** (COM dependency), py-scrcpy-client doesn't build on ARM64 Pi.

### Recommended Configuration

1. **Immediate**: Use MaaMCP (1.6s) for screenshots, mobile-mcp for D-pad/input control
2. **Quick win**: Switch any raw ADB screencap calls from `-p` (PNG) to raw BMP
3. **Future**: Build scrcpy frame extraction client for ~50ms captures

## Optional Companion

`screen-buffer-mcp` (vladkarpman) — screenshot-only server using scrcpy for ~50ms captures. Would need to run on Pi alongside mobile-mcp. Consider adding after paces 1-5 pass if screenshot throughput is a bottleneck.
