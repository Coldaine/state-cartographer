# Failure Mode Registry

A running catalog of things that break during live Azur Lane automation.

## Format

```markdown
### FM-XXX: Short Name
**Discovered:** YYYY-MM-DD  
**Severity:** Blocking | Workaroundable | Cosmetic  
**Component:** Transport | Vision | State Machine | Game Logic

**Symptom:** What happens  
**Repro Steps:** How to trigger it  
**Workaround:** Current mitigation  
**Root Cause:** (if known)  
**Fix Status:** Open | In Progress | Fixed
```

---

## Active

### FM-001: Coordinate Precision / Button Hitbox Mismatch
**Discovered:** 2026-03-28  
**Severity:** Workaroundable  
**Component:** Transport (ADB)

**Symptom:** ADB tap commands appear to have no effect; screen remains unchanged  
**Initial Misdiagnosis:** Thought to be "modal input blocking" — ADB events filtered by game  
**Actual Cause:** Coordinate calculation missed the actual clickable button region

**Repro Steps:** 
1. Victory screen with orange "Confirm" button appears
2. Tap calculated coordinates (e.g., 1150, 680)
3. No response — coordinates were outside hitbox
4. Manual inspection shows button at different position

**Workaround:** MEmu keymapping — bind semantic regions to keys (Space=Primary, Tab=Back)

**Root Cause:** 
- Visual button bounds ≠ clickable bounds
- Coordinate scaling issues between ADB and game rendering
- No feedback loop to verify tap landed

**Fix Status:** Superseded by [Keymapping Strategy](../transport/keymapping-strategy.md) — use `input keyevent` instead of `input tap` for 95% of interactions

---

### FM-002: Battle Map Coordinate Miss
**Discovered:** 2026-03-28  
**Severity:** Blocking  
**Component:** Transport / Game Logic

**Symptom:** Taps on enemy nodes (Lv.76, Lv.78) don't engage combat  
**Repro Steps:**
1. On battle map with visible enemies
2. Tap enemy coordinates (e.g., 850, 430)
3. No formation screen appears

**Workaround:** None found — user must manually click

**Root Cause Hypotheses:**
- Enemies out of fleet movement range (need to move first)
- Coordinate scaling issue (ADB vs. game coordinate space)
- Enemy hitbox smaller than visual indicator
- Fleet not in "attack mode" (need to tap something else first)

**Fix Status:** Open — needs investigation

---

### FM-003: MaaTouch Connect Timeout
**Discovered:** 2026-03-28  
**Severity:** Workaroundable  
**Component:** Transport (MaaTouch)

**Symptom:** "No response within 3.0s" on every connect  
**Repro Steps:** Connect to emulator via Pilot

**Workaround:** Automatic fallback to ADB input

**Root Cause:** MaaTouch binary not installed on emulator or port conflict

**Fix Status:** Open — low priority (ADB works)

---

### FM-004: Emulator Render Freeze
**Discovered:** 2026-03-28  
**Severity:** Workaroundable (manual restart)  
**Component:** Emulator (MEmu)

**Symptom:** Screen animations stop; game appears frozen; screenshots identical across time  
**Repro Steps:** 
- Extended play sessions
- Multiple rapid inputs

**Workaround:** Manual emulator restart; wait and retry

**Root Cause:** Unknown — possibly Vulkan rendering bug, memory leak, or MEmu instability

**Detection Idea:** Compare consecutive screenshots; if pixel-identical for >X seconds while expecting animation, flag as frozen

**Fix Status:** Open — needs heuristic detector

---

## Fixed

None yet.

---

## Legend

- **Blocking:** Halts automation, requires manual intervention
- **Workaroundable:** Has mitigation, but not ideal
- **Cosmetic:** Annoying but doesn't stop progress
