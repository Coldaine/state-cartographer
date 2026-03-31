# Keymapping Strategy: Bypassing Coordinate Precision

**Status:** PROPOSED — `press()` is now implemented in `pilot.py` as of 2026-03-30. MEmu keymapper bindings still need to be configured and exported.  
**Replaces/Extends:** `tap-chain-design.md`  
**Date:** 2026-03-28

---

## The Problem with Tap Coordinates

During live testing (2026-03-28), we discovered that ADB `input tap` has **coordinate precision issues**:

1. **Visual ambiguity**: Button hitboxes don't always match visual bounding boxes
2. **Scaling drift**: Same UI element at different positions across resolutions
3. **Modal misdiagnosis**: FM-001 was initially thought to be "input blocking" but was actually **missed coordinates**

The victory screen "Confirm" button failed not because ADB was blocked, but because our calculated coordinates landed outside the actual clickable region.

---

## The Solution: MEmu Keymapping

Instead of calculating pixel coordinates, we bind **semantic regions** to keyboard keys in MEmu's keymapper:

| Key | Semantic Region | Typical Use |
|-----|-----------------|-------------|
| `Space` | Primary Action | Attack, Battle, Confirm, Sortie |
| `Tab` | Back / Cancel | Return, Retreat, Close |
| `Enter` | Secondary Confirm | Yes, OK, Accept (when different from primary) |
| `1` | Fleet 1 Select | Main fleet focus |
| `2` | Fleet 2 Select | Sub fleet focus |
| `Q` | Engage Nearest | Target closest enemy |
| `E` | Next Objective | Boss, exit, priority target |
| `W/A/S/D` | Directional | Pan map, move fleet |
| `Esc` | System Menu | Pause, settings, abort |
| `F12` | Screenshot | Manual corpus capture |
| `F9` | Emergency Kill | App kill if frozen |

---

## Implementation

### Phase 1: MEmu Configuration

1. Open MEmu keymapper (Ctrl+Shift+K)
2. Assign keys to screen regions per table above
3. Save as `configs/azur_lane_keymap.kmp`
4. Export for version control

### Phase 2: Harness Extension

```python
class Pilot:
    """Unified transport with keymapping support."""
    
    KEYMAP = {
        "primary": 62,    # KEYCODE_SPACE
        "back": 61,       # KEYCODE_TAB
        "confirm": 66,    # KEYCODE_ENTER
        "cancel": 111,    # KEYCODE_ESCAPE
        "fleet1": 8,      # KEYCODE_1
        "fleet2": 9,      # KEYCODE_2
        "engage": 45,     # KEYCODE_Q
        "objective": 33,  # KEYCODE_E
        "up": 19,         # KEYCODE_DPAD_UP
        "down": 20,       # KEYCODE_DPAD_DOWN
        "left": 21,       # KEYCODE_DPAD_LEFT
        "right": 22,      # KEYCODE_DPAD_RIGHT
        "menu": 111,      # KEYCODE_ESCAPE
        "emergency": 120, # KEYCODE_F9
    }
    
    def press(self, action: str, count: int = 1, delay: float = 0.3) -> bool:
        """Press a mapped key by semantic name.
        
        Args:
            action: Semantic key name from KEYMAP
            count: Number of times to press
            delay: Seconds between presses
            
        Returns:
            True if all presses succeeded
        """
        keycode = self.KEYMAP.get(action)
        if not keycode:
            raise ValueError(f"Unknown key action: {action}")
        
        for _ in range(count):
            self.keyevent(keycode)
            if delay and _ < count - 1:
                time.sleep(delay)
        return True
    
    def battle_flow(self) -> None:
        """Execute full battle engagement via keys."""
        self.press("fleet1")           # Select main fleet
        time.sleep(0.5)
        self.press("engage")           # Target enemy
        time.sleep(0.5)
        self.press("primary", count=2) # Attack → Battle
        # Combat runs auto, wait for results...
    
    def dismiss_results(self, max_presses: int = 5) -> bool:
        """Spam primary action to advance through victory → drops → results → map.
        
        Returns:
            True if screen changed (corpus verification)
        """
        initial = self.screenshot()
        for _ in range(max_presses):
            self.press("primary")
            time.sleep(1.5)
            current = self.screenshot()
            if current != initial:
                return True
        return False  # No state change = possible fault
```

---

## Comparison: Tap vs Key

| Scenario | Tap Approach | Key Approach | Winner |
|----------|--------------|--------------|--------|
| Primary button (Attack, Confirm) | Calculate coords, risk miss | `press("primary")` | Key |
| Back navigation | Find arrow position | `press("back")` | Key |
| Fleet selection | Tap chibi coordinates | `press("fleet1")` | Key |
| Enemy targeting (specific) | Precise coordinate | `press("engage")` for nearest | Depends |
| Unknown/new screen | Blind tap possible | No mapping = fallback to tap | Tap |

---

## Hybrid Strategy

Use **keys for 95%**, **taps for edge cases**:

```python
def smart_interact(self, target_type: str, fallback_coords: tuple | None = None):
    """Try key first, fallback to coordinate tap."""
    if target_type in self.KEYMAP:
        return self.press(target_type)
    elif fallback_coords:
        return self.tap(*fallback_coords)
    else:
        raise ValueError(f"No key or coords for {target_type}")
```

---

## Migration from tap_chain()

| Old tap_chain Step | New key_chain Step |
|-------------------|-------------------|
| `tap(1150, 680)` for Confirm | `press("primary")` |
| `tap(50, 50)` for Back arrow | `press("back")` |
| `tap(850, 430)` for enemy | `press("engage")` or keep coordinate |

---

## Risk: Keymap Drift

If game UI changes (update, different device), key mappings may point to wrong regions.

**Mitigation:**
- Store keymap profile in repo
- Version control with game version notes
- Periodic verification corpus

---

## Related Documents

- [tap-chain-design.md](./tap-chain-design.md) — Predecessor approach
- [failure-mode-registry.md](../sessions/failure-mode-registry.md) — FM-001 correction
- [2026-03-28-live-battle-pilot.md](../sessions/2026-03-28-live-battle-pilot.md) — Live session notes
