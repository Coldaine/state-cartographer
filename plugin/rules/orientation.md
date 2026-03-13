---
name: Orientation & State Confirmation
description: Always-on rule governing how the agent confirms its current state, handles ambiguity, and recovers when lost.
type: rule
applies_to: all_phases
priority: high
---

# Orientation & State Confirmation

## The Orientation Workflow

### Step 1: Passive Classification (Cheap)

```bash
python plugin/scripts/locate.py --graph graph.json --session session.json
```

Returns one of three outcomes:

**Outcome A: Definitive State (Confidence > 85%)**
Proceed. You know where you are.

**Outcome B: Ambiguous State (2+ candidates)**
Go to Step 2: Active Disambiguation.

**Outcome C: Unknown State (No candidates match)**
Go to Step 3: Unknown State Recovery.

---

### Step 2: Active Disambiguation (Medium Cost)

`locate()` suggests disambiguation probes ranked by information value. Execute them:

```bash
# Example: check if DOM element ".ship-list" is present
# This distinguishes "dock" from "formation"
```

Most ambiguities resolve in 1–2 probes. Rank probes by **information value**, not cost alone.

After disambiguation:
```bash
python plugin/scripts/session.py confirm --state dock --session session.json
```

---

### Step 3: Unknown State Recovery

Options (in order of preference):

**Option A: Pinpoint the Unknown State (5 min time box)**
1. Take screenshot
2. Analyze with vision
3. Compare to known states
4. If match found → update graph, update session

**Option B: Navigate to Known State**
1. Try system back button 3 times
2. Try navigating to home/main menu
3. Reinit session from known state

**Option C: Fresh Start (last resort)**
1. Close and reopen app
2. Go through entry workflow
3. Reinit session

**Option D: Escalate to Human**
If 10+ minutes trying to reorient with no progress.

---

## Confirmation After Transitions

**Every transition is a hypothesis.** After taking an action:

1. Execute transition action
2. Wait expected latency
3. Call `locate()` to confirm new state
4. Was the new state what you expected?
   - YES → update session, continue
   - MAYBE (ambiguous) → go to Step 2
   - NO (unexpected) → investigate or retry (max 2 retries)

---

## Flagging Unknowns

When encountering a state not in the graph, document it:
- Time, previous state, action taken
- Observations and screenshot
- Assessment and recommendation (add to graph or investigate)

These unknowns become new states in Phase 6 (Maintenance).

---

## Transient vs. Structural Changes

- If the **underlying structure** is the same with only an overlay added: same state
- If the **entire screen changed** to different layout/elements: different state

Decision rule: Does anchor check still pass? If yes → same state with transient overlay.

---

## Session History as Disambiguation

Session history dramatically reduces ambiguity. Example:
- History says you were at `dock` and clicked something
- Only `formation` and `ship_detail` are reachable from `dock` in one click
- Check anchors for those two → resolve immediately

**Always maintain session history.**

---

## Orientation Checklist

Before taking any action:

- [ ] Ran `locate()` (with or without session)
- [ ] Result is definitive OR resolved via probes
- [ ] Session updated with confirmed state
- [ ] State is in graph
- [ ] If unknown state, documented and escalated

---

## Summary

```
Where am I?
   → locate() (passive, cheap)
   ├─ Definitive? → proceed
   ├─ Ambiguous? → active disambiguation
   │   ├─ Resolved? → proceed
   │   └─ Still ambiguous? → vision review
   └─ Unknown? → recover or escalate

After every action:
   → locate() → verify new state matches expected
   ├─ YES → continue
   ├─ MAYBE → disambiguate
   └─ NO → investigate or retry
```

Orientation is not optional. You must know where you are before deciding what to do next.
