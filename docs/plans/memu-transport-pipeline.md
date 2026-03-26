# Plan: MEmu Transport Pipeline

> **Status: Substantially complete (2026-03-26).**
> Health check, capture, and integration phases are done. Emulator daemon (Phase 1) is deferred — not needed until unattended ops. Capture engineering (FrameRing, fallback chain) deferred — Vulkan eliminated the failure mode. See `docs/decisions.md` for the full rationale.
>
> This plan was written when ADB screencap was broken on OpenGL. The multi-method fallback chain is no longer needed. See `docs/transport-methods.md` for the current method selection logic.

## Goal

Build a robust transport pipeline that:
1. Monitors emulator state (MEmu daemon)
2. Verifies connectivity before attempting capture
3. Uses ADB screencap as primary capture (Vulkan makes this 100% reliable)
4. Can launch MEmu with admin privileges when needed

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TRANSPORT PIPELINE                              │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 1. EMULATOR DAEMON                                              │   │
│  │    - Monitor MEmu process state                                 │   │
│  │    - Auto-launch MEmu if not running                            │   │
│  │    - Request admin elevation when needed                         │   │
│  │    - Track emulator serial, port, render mode (OpenGL/DX)      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                         │
│                              ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 2. HEALTH CHECK                                                │   │
│  │    - Is ADB daemon running?                                     │   │
│  │    - Is emulator accessible? (verify serial)                    │   │
│  │    - Is game running? (check package)                          │   │
│  │    - Network ADB enabled? (port 5555)                          │   │
│  │    - Rendering mode known? (OpenGL/DirectX/Vulkan)              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                         │
│                              ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 3. CAPTURE (ADB screencap on Vulkan — 100% reliable)            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                         │
│                              ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 4. CAPTURE VERIFICATION                                         │   │
│  │    - Verify non-zero bytes                                      │   │
│  │    - Verify valid PNG header                                    │   │
│  │    - Pixel analysis: black frame detection                       │   │
│  │    - Immediate retries (no artificial delay)                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                         │
│                              ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 5. LOGGING / TELEMETRY                                          │   │
│  │    - Every attempt logged with: timestamp, method, result       │   │
│  │    - Failure modes categorized                                   │   │
│  │    - Correlation data for analysis                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Critical Finding (2026-03-25): Vulkan Solves Capture

The original blocker was specific to MEmu OpenGL. Once MEmu is configured for Vulkan, plain ADB screencap becomes reliable enough to serve as the primary capture path.

From the probe and stress-test evidence:

- On **OpenGL**, ADB screencap can return empty or stale frames
- On **Vulkan**, ADB screencap produced 316/316 good frames with zero failures, black frames, or corruption
- MaaFramework remains a useful reference and possible fallback, but it is no longer the architectural center

**Current capture order:**
1. **ADB screencap** on Vulkan
2. MaaFramework only if Vulkan assumptions are violated or later telemetry proves a gap

## Historical Note

This document originally centered on a multi-method CaptureManager because the repo was still operating under OpenGL-era assumptions. Keep those archived ideas as reference only. The active architecture is documented in `docs/transport-methods.md` and `docs/decisions.md`.

## Component Specifications

### 1. Emulator Daemon (`state_cartographer/daemon/emulator.py`)

```python
class EmulatorDaemon:
    """Monitors and manages MEmu emulator lifecycle."""
    
    def __init__(self, config: EmulatorConfig):
        self.config = config
        self.process = None
        self.serial = config.serial
        self.admin_elevation = config.needs_admin
    
    def is_running(self) -> bool:
        """Check if MEmu process is running."""
        # Query MEmu process list
        pass
    
    def launch(self, admin: bool = False) -> bool:
        """Launch MEmu, optionally with admin elevation."""
        if admin:
            # Use subprocess + UAC elevation
            # MEmuConsole.exe supports command-line launch
            pass
        else:
            # Normal launch
            pass
    
    def get_state(self) -> EmulatorState:
        """Return comprehensive emulator state."""
        return EmulatorState(
            process_running=self.is_running(),
            adb_accessible=self.check_adb(),
            game_running=self.check_game(),
            render_mode=self.detect_render_mode(),
            serial=self.serial,
        )
```

### 2. Health Check (`state_cartographer/transport/health.py`)

```python
@dataclass
class HealthReport:
    adb_daemon_up: bool
    device_responding: bool
    correct_serial: bool
    game_package_present: bool
    render_mode: str  # "opengl", "directx", "vulkan", "unknown"
    network_adb_enabled: bool

def health_check(adb: Adb, serial: str, package: str) -> HealthReport:
    """Comprehensive health check before capture."""
    pass
```

### 3. Capture (Simplified — Vulkan)

> The multi-method CaptureManager was designed for the OpenGL era. On Vulkan, ADB screencap is 100% reliable. The existing `state_cartographer/transport/capture.py` handles this with no fallback chain needed.

See `docs/transport-methods.md` for the current capture architecture.

### ~~3. Capture Manager with Fallback~~ (Archived — OpenGL era)

```python
class CaptureManager:
    """Multi-method screenshot capture with fallback."""
    
    def __init__(self, adb: Adb):
        self.adb = adb
        self.current_method = None
        self.droidcast_port = 53516
        
    def capture(self, max_retries: int = 3) -> bytes | None:
        """Try capture methods in order until one works.
        
        Retry pattern: immediate retries within each method.
        ADB round-trip is ~100ms minimum, so no artificial delay needed —
        the next command naturally occurs ~100ms later, giving the framebuffer
        time to sync.
        
        If all retries for a method fail, move to the next method immediately.
        """
        
        # Method 1: ADB screencap
        for attempt in range(max_retries):
            data = self._try_screencap()
            if self._is_valid(data):
                self.current_method = "screencap"
                return data
            # No sleep here — ADB RT ~100ms is delay enough
        
        # Method 2: DroidCast
        self._ensure_droidcast_running()
        for attempt in range(max_retries):
            data = self._try_droidcast()
            if self._is_valid(data):
                self.current_method = "droidcast"
                return data
        
        # Method 3: scrcpy stream
        self._ensure_scrcpy_running()
        for attempt in range(max_retries):
            data = self._try_scrcpy_frame()
            if self._is_valid(data):
                self.current_method = "scrcpy"
                return data
        
        # Method 4: Win32 PrintWindow (host-side)
        for attempt in range(max_retries):
            data = self._try_printwindow()
            if self._is_valid(data):
                self.current_method = "win32_printwindow"
                return data
        
        return None  # All methods failed
    
    def _is_valid(self, data: bytes | None) -> bool:
        """Verify capture is non-zero and not black."""
        if data is None or len(data) == 0:
            return False
        if len(data) < 1000:  # Likely just system chrome
            return False
        # Additional pixel analysis
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return False
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if (gray < 10).mean() > 0.95:  # >95% black
            return False
        return True
```

### 4. Win32 PrintWindow Backup (Host-Side Vision)

```python
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

def printwindow(hwnd: int) -> bytes | None:
    """Capture window content using Win32 PrintWindow API.
    
    This is a LAST RESORT when all ADB methods fail.
    It captures from the host side, bypassing the emulator's framebuffer entirely.
    """
    hwnd = wintypes.HWND(hwnd)
    
    # Get window dimensions
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    
    # Create compatible DC and bitmap
    dc = user32.GetDC(hwnd)
    mfc_dc = ctypes.windll.gdi32.CreateCompatibleDC(dc)
    bitmap = ctypes.windll.gdi32.CreateCompatibleBitmap(dc, width, height)
    ctypes.windll.gdi32.SelectObject(mfc_dc, bitmap)
    
    # Print the window
    user32.PrintWindow(hwnd, mfc_dc, 0)
    
    # Copy to buffer
    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth = width
    bmi.biHeight = -height  # Negative for top-down
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0  # BI_RGB
    
    buf_len = width * height * 4
    buf = (ctypes.c_ubyte * buf_len)()
    ctypes.windll.gdi32.GetDIBits(mfc_dc, bitmap, 0, height, buf, ctypes.byref(bmi), 0)
    
    # Cleanup
    user32.ReleaseDC(hwnd, dc)
    ctypes.windll.gdi32.DeleteObject(bitmap)
    ctypes.windll.gdi32.DeleteDC(mfc_dc)
    
    # Convert to PNG
    img = np.frombuffer(buf, dtype=np.uint8).reshape((height, width, 4))
    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    _, png = cv2.imencode('.png', img)
    return png.tobytes()
```

## Implementation Steps

### Phase 1: Emulator Daemon
1. Create `state_cartographer/daemon/emulator.py`
2. Implement process monitoring (is MEmu running?)
3. Implement MEmuConsole launch (with admin elevation support)
4. Add to `state_cartographer/transport/__init__.py`

### Phase 2: Health Check Layer
1. Create `state_cartographer/transport/health.py`
2. Implement `health_check()` function
3. Detect render mode (OpenGL/DirectX/Vulkan)
4. Verify game package presence

### Phase 3: Capture (done — further engineering deferred)
1. `state_cartographer/transport/capture.py` — ADB screencap on Vulkan, synchronous, sufficient
2. Capture verification (black frame detection) in `scripts/stress_test_adb.py`
3. FrameRing / ring buffer / capture thread — deferred 2026-03-26 (Vulkan eliminated the failure mode). Design in `docs/RES-research/RES-frame-ring-design.md` if needed later.
4. Multi-method fallback chain — deferred (see `docs/transport-methods.md`)

### Phase 4: Integration
1. Update `state_cartographer/transport/__init__.py`
2. Wire into existing Pilot facade
3. Add telemetry logging

## Render Mode Detection

```python
def detect_render_mode(adb: Adb) -> str:
    """Detect how MEmu is rendering graphics."""
    # Check for OpenGL
    gl_info = adb.shell(['dumpsys', 'SurfaceFlinger', '|', 'grep', 'GLES'])
    
    # Check for DirectX (Windows-specific)
    dx_info = adb.shell(['getprop', 'persist.sys.emulator.directx'])
    
    # Check for Vulkan
    vk_info = adb.shell(['dumpsys', 'vulkan'])
    
    # Return detected mode
    if "enabled" in gl_info or "on" in gl_info:
        return "opengl"
    elif "1" in dx_info:
        return "directx"
    elif "vulkan" in vk_info:
        return "vulkan"
    return "unknown"
```

## Files to Create/Modify

```
state_cartographer/
├── daemon/
│   ├── __init__.py
│   └── emulator.py          # NEW: EmulatorDaemon
├── transport/
│   ├── health.py             # DONE: HealthCheck
│   ├── capture.py            # DONE: ADB screencap
│   ├── adb.py                # DONE: adbutils wrapper
│   └── pilot.py             # MODIFY: Wire observation layer
```

## Testing

```bash
# Test emulator daemon
uv run python -c "
from state_cartographer.daemon.emulator import EmulatorDaemon
d = EmulatorDaemon()
print(d.get_state())
"

# Test health check
uv run python -m state_cartographer.transport.health --serial 127.0.0.1:21513

# Test capture (stress test)
uv run python scripts/stress_test_adb.py --burst --count 10
```
