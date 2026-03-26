# MEmu Emulator Reference

## Purpose

Operational reference for the MEmu Android emulator: its architecture, how to talk to it, and what breaks when.

This doc answers: **how does MEmu actually work at the transport level, what port scheme does it use, and what capture/control methods are available to agents?**

See also:
- [backend-lessons.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/backend-lessons.md) — design constraints from past emulator work
- [testingADB.md](/mnt/d/_projects/MasterStateMachine/docs/dev/testingADB.md) — live testing plan for the pinned MEmu setup
- [substrate-and-implementation-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/substrate-and-implementation-plan.md) — tool selection decision

## Architecture

MEmu runs Android inside a VirtualBox VM (or Hyper-V on newer versions). The Android OS runs on a virtualized ARM/x86 architecture with its own framebuffer — not a standard Windows window.

This is why standard Windows screen capture APIs (`PrintWindow`, `BitBlt`) return black screens. The Android framebuffer is not a GDI surface; it lives inside the VM guest.

## ADB Port Structure

Each MEmu instance exposes ADB on predictable ports:

| Instance | ADB Address |
|---|---|
| First (index 0) | `127.0.0.1:21503` |
| Second (index 1) | `127.0.0.1:21513` |
| Third (index 2) | `127.0.0.1:21523` |

Pattern: `21503 + (instance_index * 10)`

The pinned instance for this repo is controlled by `configs/memu.json` (currently `127.0.0.1:21513`), so do not hard-code `21503` in runtime code.

## Frame Capture Methods

Three methods exist, ordered by reliability for agent use.

### Method 1: ADB Screencap (Reliable, Slow)

```python
import subprocess
import numpy as np
from PIL import Image
import io

def get_frame_memu(instance=0):
    port = 21503 + (instance * 10)
    result = subprocess.run(
        ['adb', '-s', f'127.0.0.1:{port}', 'exec-out', 'screencap', '-p'],
        capture_output=True
    )
    if result.returncode == 0:
        img = Image.open(io.BytesIO(result.stdout))
        return np.array(img)
    return None
```

- Works even when window minimized or hidden
- ~100–300ms per frame, high CPU overhead
- Subject to `FLAG_SECURE` — returns black frames for protected surfaces (see Admin Constraints below)

### Method 2: MEmuManage.exe screenshotpng (VM-level, Fast)

MEmu runs on a VirtualBox fork. The `MEmuManage.exe` tool (in `C:\Program Files\Microvirt\MEmuHyperv\`) exposes VirtualBox's `screenshotpng` command, which captures directly from the VM framebuffer.

```bash
# Capture screenshot from VM "MEmu" (default instance name)
MEmuManage.exe screenshotpng MEmu C:\path\to\save.png
```

```python
import subprocess
from PIL import Image
import numpy as np

def memu_vm_screenshot(vm_name="MEmu", output_path="frame.png"):
    manage_path = r"C:\Program Files\Microvirt\MEmuHyperv\MEmuManage.exe"
    subprocess.run([
        manage_path,
        "screenshotpng",
        vm_name,
        output_path
    ])
    return np.array(Image.open(output_path))
```

- Faster than ADB screencap — reads the VM framebuffer directly
- Requires `MEmuManage.exe` (may require admin elevation — see Admin Constraints)
- Instance names can be listed with `MEmuManage.exe list vms` or via Multi-MEmu manager

### Method 3: Direct Window Handle (Fast, Fragile)

WinAPI capture via `win32gui`. Only works when the MEMU window is visible (not minimized).

```python
import win32gui
import win32ui
import win32con

hwnd = win32gui.FindWindow(None, "MEmu")
rect = win32gui.GetWindowRect(hwnd)
width = rect[2] - rect[0]
height = rect[3] - rect[1]

hwndDC = win32gui.GetWindowDC(hwnd)
mfcDC = win32ui.CreateDCFromHandle(hwndDC)
saveDC = mfcDC.CreateCompatibleDC()

saveBitMap = win32ui.CreateBitmap()
saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
saveDC.SelectObject(saveBitMap)

result = win32gui.PrintWindow(hwnd, saveDC.GetSafeHdc(), 1)
```

- Returns **black** if MEMU is rendering via GPU acceleration
- Requires disabling GPU acceleration in MEMU settings: `Engine → Render Mode → DirectX` or `Safe Mode`
- Breaks if the window is minimized or occluded

### Method 4: ADB Screenrecord (Real-time Stream)

Pipe raw H.264 video and decode frames from the stream:

```bash
adb -s 127.0.0.1:21503 shell screenrecord --output-format=h264 - | \
  ffmpeg -i - -f image2pipe -pix_fmt rgb24 -vcodec rawvideo -
```

Then read frames from the pipe in the agent loop. Lower latency than screencap per-frame but higher complexity.

## Admin Constraints

`memuc.exe` (MEmu's CLI controller) requires administrator elevation on the host. This is a problem for programmatic automation running in user-space processes.

### Option A: Pre-launch + ADB (Recommended)

MEmu is a long-lived process — start it once, it stays running. ADB does **not** require admin once MEmu is up. The agent connects via ADB for all control and capture.

**One-time setup — create a scheduled task that starts MEmu at login:**

```powershell
schtasks /create /tn "StartMEmu" /tr '"C:\Program Files\Microvirt\MEmu\MEmu.exe"' /sc onlogon /rl highest
```

This runs elevated at every login, starts MEmu, then the task exits. MEmu keeps running. No daemon, no service.

**Agent startup — check ADB is reachable before proceeding:**

```python
import subprocess
import time

class MEMUAgent:
    def __init__(self, port=21503):
        self.serial = f"localhost:{port}"
        self._ensure_connected()

    def _ensure_connected(self, retries=5, delay=3):
        for attempt in range(retries):
            result = subprocess.run(
                ['adb', 'connect', self.serial],
                capture_output=True, text=True
            )
            if 'connected' in result.stdout.lower():
                return
            time.sleep(delay)
        raise RuntimeError(f"Cannot reach MEmu on {self.serial} after {retries} attempts")

    def tap(self, x, y):
        subprocess.run(['adb', '-s', self.serial, 'shell', 'input', 'tap', str(x), str(y)])

    def get_screen(self):
        r = subprocess.run(
            ['adb', '-s', self.serial, 'exec-out', 'screencap', '-p'],
            capture_output=True
        )
        return r.stdout
```

If ADB connection fails, the agent knows MEmu isn't running and can report it. No elevated daemon needed on the agent side.

### Option B: LDPlayer Alternative

LDPlayer does not require admin for its CLI tool (`dnconsole.exe`):

```bash
"C:\LDPlayer\LDPlayer9\dnconsole.exe" launch --name "Instance0"
"C:\LDPlayer\LDPlayer9\dnconsole.exe" adb --name "Instance0" --command "shell input tap 500 500"
```

ADB port: `5555` (or `5554+` for multi-instance). Consider if MEmu admin requirements become a blocking constraint.

## FLAG_SECURE Handling

Some game surfaces set Android's `FLAG_SECURE`, which causes ADB `screencap` and `screenrecord` to return black frames. This is a guest-side Android policy, not a host-side emulator issue.

**Diagnose before fixing — don't guess:**

```bash
# Test 1: Home screen vs target app
# Make sure MEMU is running, connect:
adb connect 127.0.0.1:21503

# Screenshot the home screen (should work)
adb shell screencap -p /sdcard/test_home.png
adb pull /sdcard/test_home.png

# Now open your target app manually, then:
adb shell screencap -p /sdcard/test_app.png
adb pull /sdcard/test_app.png
```

Interpretation:
- Home screen visible, app = black → **FLAG_SECURE** (fix below)
- Both black → GPU/render issue (try Method 3 with software render mode)
- Both visible → **FLAG_SECURE is not your problem** — ADB screencap works fine

```bash
# Test 2: Check window flags directly
adb shell dumpsys window | grep -i "flags=" | grep -i "secure"
# If FLAG_SECURE appears, confirmed

# Test 3: UI Automator dump (captures UI hierarchy even when pixels are blocked)
adb shell uiautomator dump /sdcard/window_dump.xml
adb pull /sdcard/window_dump.xml
# If this XML has content, UI is accessible even if screencap is black
```

**If FLAG_SECURE is confirmed and visual feedback is needed:**

1. Enable root in MEmu settings (`Settings → Other Settings → Root Mode`)
2. Install Magisk + LSPosed (Zygisk version)
3. Install the "Disable FLAG_SECURE" module
4. Enable the module in LSPosed manager, select `System Framework` + target app
5. ADB screenshots will now return real frames

**If coordinate-based blind tapping is sufficient, `FLAG_SECURE` is irrelevant** — ADB input commands always work regardless.

## Emulator Alternatives

**Google Android Emulator** — no admin, but unsuitable for 3D games. Renders via software or slow GPU emulation. Use only for 2D apps or lightweight testing.

**LDPlayer** — MEmu's main competitor. Gaming-optimized (often better than MEmu for 3D). Its `dnconsole.exe` CLI works without admin elevation. ADB port `5555`. Consider this if MEmu's admin requirement becomes a blocking constraint.

## Recommended Agent Setup

1. **Verify ADB connectivity first**: `adb connect 127.0.0.1:21503` — confirm the port is reachable before anything else.
2. **Diagnose FLAG_SECURE**: Run the home-screen vs app test above before applying root/LSPosed fixes.
3. **Use ADB screencap for frames** (baseline reliability) or `MEmuManage.exe screenshotpng` for speed if admin is available.
4. **Use ADB ports for control**: tap, swipe, key events via `adb shell input` — always work regardless of FLAG_SECURE.
5. **Root + LSPosed** only if visual feedback on FLAG_SECURE surfaces is required — don't apply it preemptively.
