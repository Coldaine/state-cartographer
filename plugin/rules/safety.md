---
name: Safety & Confidence Thresholds
description: Always-on rule defining confidence requirements, escalation paths, and guards against irreversible actions.
type: rule
applies_to: all_phases
priority: critical
---

# Safety & Confidence Thresholds

## Confidence Tiers

### Tier 1: Exploratory / Low Risk (70% confidence OK)

States where wrong classification is merely inconvenient, not destructive (e.g., `main_menu`, `dock`, `settings`).

**Rule:** If `locate()` returns 70%+ confidence, proceed with a note in the session log.

### Tier 2: Moderate Risk / Consequential (85% confidence required)

States where wrong classification causes side effects but not permanent damage (e.g., `confirm_sell_equipment`, `navigation_to_battle`).

**Rule:** If 85%+ confidence, proceed. If 70–84%, escalate to vision review (screenshot + LLM judgment).

### Tier 3: Irreversible / Critical (99% confidence required)

States representing points of no return (e.g., `confirm_purchase_diamonds`, `confirm_retire_fleet_ship`, `factory_reset_data`).

**Rule:** If less than 99% confidence, **STOP**. Options:
1. Vision review: screenshot + LLM judgment
2. Escape to safe state: navigate back to entry point
3. Escalate to human: "I'm 95% sure, but I need 99%. Please verify."

---

## Escalation Path

```
Confidence too low
   → Take screenshot
   → Analyze with vision / LLM
   → Confidence > threshold?
     YES → proceed
     NO  → human escalation
```

---

## The "Unknown State" Scenario

When `locate()` returns "I have no idea where I am":

1. **Do not take any action.** Do not guess.
2. Take a screenshot and DOM dump
3. Try to identify the state manually (session history, familiar UI elements)
4. If identified → update session, proceed
5. If still unknown → navigate to known state, or escalate to human

---

## Action Guards

### Guard 1: Irreversible Action Confirmation

Before any transition marked `irreversible: true`:
- Confirm `locate()` returns 99%+ confidence, OR
- Get vision review + human confirmation, OR
- Do not proceed.

### Guard 2: Fragile Transition Fallback

For transitions marked `fragile: true`:
1. Try deterministic action
2. Run `locate()` to confirm state changed
3. If unexpected result → trigger fallback (vision recovery)

### Guard 3: Session Validation

Before any action:
1. Confirm session is initialized
2. Confirm current state is known

If corrupted → reinitialize from known entry point.

---

## Timeout & Lag Guards

If a transition exceeds `max_latency_ms`:
1. Run `locate()` to check state
2. If state didn't change → investigate or retry
3. If appears stuck → screenshot + escalate

---

## Session Integrity Checks

Every 5–10 actions:
1. Run `locate()` without session history
2. Compare to session-augmented result
3. If they differ → session may be corrupted → reinit or escalate

---

## Summary

1. **Low-risk states**: 70% confidence OK
2. **Moderate-risk states**: 85% required, else escalate to vision
3. **Irreversible states**: 99% required, else escalate to human
4. **Unknown state**: Never guess. Always escalate.
5. **Fragile transitions**: Always verify state changed after action
6. **Session integrity**: Periodically validate against live state
