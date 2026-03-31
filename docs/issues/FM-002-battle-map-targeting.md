# FM-002: Battle Map Enemy Targeting

**Status:** Open  
**Severity:** Blocking  
**Component:** Transport / Game Logic  
**Discovered:** 2026-03-28

---

## Problem

Tapping enemy nodes on the battle map does not consistently engage combat. Multiple coordinate attempts failed to trigger the formation screen.

## Evidence

From `tmp/engage_011142.png` and `tmp/lv78_011320.png`:
- Tried coordinates: (850, 430), (980, 420), (860, 145)
- No formation screen appeared
- Fleet remained stationary

## Hypotheses

1. **Range limitation**: Enemies outside fleet movement range cannot be engaged directly
2. **Two-phase interaction**: Must tap fleet first to select, then tap destination/enemy
3. **Coordinate scaling**: ADB coordinates may not match game's internal grid
4. **Animation state**: Input ignored while fleet moving or UI animating
5. **Wrong target type**: Lv.76/Lv.78 enemies may be bosses requiring different interaction

## Reproduction Steps

1. Enter battle map with visible enemies (Lv.76, Lv.78)
2. Attempt ADB tap at enemy coordinates
3. Observe: no response, no formation screen

## Workarounds

- **None found** — requires manual intervention or keymapping (Q=Engage nearest)

## Proposed Investigation

### Option A: Keymapping Fix
Bind `Q` key to "Engage nearest enemy" in MEmu. Test if this works where coordinate taps fail.

### Option B: State-Aware Targeting
1. Screenshot before tap
2. Tap fleet chibi to ensure selection
3. Wait for movement range highlight
4. Tap within highlighted cells only
5. Verify formation screen appeared

### Option C: Grid Coordinate Calibration
Map screenshot pixels to game grid cells:
- Identify grid cell size from visual grid lines
- Calculate valid movement range from fleet position
- Only tap enemies within reachable cells

## Acceptance Criteria

- [ ] Can consistently engage enemies via automation
- [ ] Works for both normal mobs and boss nodes
- [ ] Fallback to keymapping if coordinate targeting unreliable

## Related

- [Keymapping Strategy](../transport/keymapping-strategy.md)
- [Live Session Log](../sessions/2026-03-28-live-battle-pilot.md)
