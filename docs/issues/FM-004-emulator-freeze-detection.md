# FM-004: Emulator Freeze Detection

**Status:** Open  
**Severity:** Workaroundable (manual restart)  
**Component:** Health Check / Emulator  
**Discovered:** 2026-03-28

---

## Problem

MEmu occasionally freezes during extended sessions. Animations stop, game becomes unresponsive, automation hangs indefinitely.

## Evidence

During live session (1:19am), emulator stopped responding:
- Screenshots became pixel-identical across time
- No error from ADB — connection remained open
- Game appeared visually "stuck" mid-animation

## Root Cause

Unknown. Suspected:
- Vulkan rendering bug (MEmu uses Vulkan)
- Memory leak in extended play
- MEmu instability under rapid input

## Detection Strategy

### Heuristic: Screenshot Comparison

```python
def detect_freeze(self, threshold_seconds: float = 10.0) -> bool:
    """Detect emulator freeze by comparing consecutive screenshots.
    
    Returns True if screenshots are pixel-identical for longer
    than threshold while expecting animation.
    """
    interval = 2.0  # seconds between samples
    samples_needed = int(threshold_seconds / interval)
    
    samples = []
    for _ in range(samples_needed):
        samples.append(self.screenshot_png())
        time.sleep(interval)
    
    # Check if all samples are identical
    first = samples[0]
    return all(s == first for s in samples[1:])
```

### Limitations

- False positive if game is legitimately static (loading screen, menu)
- Requires "expecting animation" context
- PNG comparison is slow; consider perceptual hash or region sampling

## Recovery Procedure

1. **Detect**: Freeze heuristic triggers
2. **Log**: Timestamp, last action, screenshot
3. **Restart**: Kill MEmu process, restart emulator
4. **Reconnect**: Re-establish ADB connection
5. **Resume**: Return to previous state (if known) or human escalation

## Implementation

### Phase 1: Detection Only

Add `health_check()` to Pilot:
- Optional freeze detection during long waits
- Log warning if potential freeze detected
- Human decides action

### Phase 2: Auto-Recovery

- Configurable auto-restart on freeze detection
- Escalation if restart fails N times
- State preservation for resume (where possible)

## Acceptance Criteria

- [ ] Freeze detection works in <15 seconds
- [ ] <5% false positive rate
- [ ] Auto-recovery procedure documented
- [ ] Graceful degradation to human escalation

## Related

- [Live Session Log](../sessions/2026-03-28-live-battle-pilot.md)
- `tmp/memu_check_011932.png` — Frozen state screenshot
