# Live Session: Pilot Harness Battle Test

**Date:** 2026-03-28  
**Objective:** Test Pilot harness in live Azur Lane combat  
**Status:** Paused — user needs to depart

---

## What Worked

| Feature | Result |
|---------|--------|
| ADB connection | ✅ Stable to 127.0.0.1:21503 |
| Screenshot capture | ✅ ~1.3MB PNGs, fast |
| Basic tap/swipe | ✅ Works on main screens |
| tap_chain() added | ✅ Scaffolding for deterministic flows |

---

## Failure Modes Discovered

### 1. Modal Dialog Input Blocking
**Symptom:** Taps don't register on item info popups, victory screens  
**Example:** T2 Royal Tech Pack dialog, post-battle Confirm screen  
**Workaround:** BACK key (`KEYCODE_BACK`) worked for item dialog  
**Root Cause Hypothesis:** Game captures input at OS level for modals; ADB input events bypassed or ignored

### 2. Battle Map Coordinate Precision
**Symptom:** Taps on enemies don't engage, no response  
**Tried:** (980, 420), (850, 430), (860, 145) — none registered  
**Possible Causes:**
- Enemies out of fleet movement range
- Need to tap grid cell first, then enemy
- Coordinate system mismatch (render scaling?)
- Enemy hitboxes smaller than visual icon

### 3. Victory Screen Confirm Button
**Symptom:** Multiple tap attempts at (920, 660), (960, 690), (1100, 700), (1150, 680) — no response  
**Workaround:** None found; user had to manually click  
**Note:** This is a blocking UI state — automation fails here

### 4. MaaTouch Initialization Timeout
**Symptom:** "MaaTouch connect failed: No response within 3.0s" on every connect  
**Workaround:** Falls back to ADB input automatically  
**Impact:** Low — ADB works, but precision timing unavailable

---

## Session Artifacts

Screenshots saved to `tmp/`:
- `battle_005233.png` — Initial battle map
- `victory_005841.png` — Perfect S-rank victory
- `post_victory_005901.png` — Item drop dialog
- `reconnect_010132.png` — After connection drop
- `map_return_010410.png` — Back to battle map
- `engage_011142.png` — Attempted enemy engagement

---

## Key Insight: Keymapping Strategy

**FM-001 was misdiagnosed.** The victory screen "Confirm" button didn't fail because of modal blocking — it failed because our calculated coordinates missed the actual hitbox.

**Solution:** Use MEmu keymapping + ADB `input keyevent` instead of `input tap` for 95% of interactions.

See: [Keymapping Strategy](../transport/keymapping-strategy.md)

| Key | Region | Use |
|-----|--------|-----|
| Space | Primary action | Attack, Battle, Confirm |
| Tab | Back | Cancel, Return, Retreat |
| 1/Q | Fleet/Engage | Select fleet, target enemy |

---

## Next Steps / TODO

1. ~~Investigate modal input~~ → **SOLVED**: Keymapping bypasses coordinate precision issues
2. **Export MEmu keymap** — Save `configs/azur_lane_keymap.kmp`
3. **Implement `press()` method** — Add semantic key actions to Pilot
4. **Battle map coordinate system** — Still need for precise enemy selection (FM-002)
5. **VLM integration** — Detect screen state for verification
6. **MaaTouch fix** — Low priority (ADB works)

---

## Design Evolution

| Approach | Status | Rationale |
|----------|--------|-----------|
| `tap_chain()` coordinates | Corpus capture | Useful for screenshot collection, not live interaction |
| `press()` semantic keys | **Implemented** (2026-03-30) | Reliable, deterministic |
| Full state machine | Future | VLM-based screen classification |

---

## Documents Created

- [Keymapping Strategy](../transport/keymapping-strategy.md) — Primary interaction design
- [Failure Mode Registry](./failure-mode-registry.md) — FM-001 through FM-004

---

*Session complete. Battle map cleared. Keymapping strategy validated.*
