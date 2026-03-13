---
name: Graph Maintenance
description: Always-on rule for keeping state graphs synchronized with external system changes.
type: rule
applies_to: all_phases
priority: medium
---

# Graph Maintenance

## When to Update the Graph

Update the graph when any of these occur during operation:

1. **`locate()` returns unknown state** — A screen not in the graph was encountered
2. **Anchor fails** — A previously-working anchor no longer matches
3. **Transition fails** — A deterministic action no longer produces the expected result
4. **New feature discovered** — The external system added new screens or flows

## Update Workflow

### 1. Capture the Anomaly

```bash
python plugin/scripts/mock.py capture \
  --state suspected_state_name \
  --screenshot screenshot.png \
  --notes "Description of what happened"
```

### 2. Diagnose

- Is this a genuinely new state? → Add to graph
- Did an anchor break? → Update the anchor selector/pattern
- Did a transition target change? → Update the transition's `to` field
- Did a transition action change? → Update the action specification

### 3. Update graph.json

Edit the graph definition directly. For new states, add anchors. For broken transitions, update actions.

### 4. Revalidate

```bash
python plugin/scripts/schema_validator.py --graph graph.json
python plugin/scripts/mock.py validate --graph graph.json
```

### 5. Test

If you have live access, test the updated anchors/transitions against the system.

## Continuous Improvement Opportunities

Every session is a chance to:
- **Validate anchors**: Do existing anchors still work?
- **Discover states**: Did the system add new screens?
- **Test transitions**: Are deterministic actions still reliable?
- **Replace transitions**: Can any remaining vision-required transitions become deterministic?

## Don't Over-Maintain

Not every anomaly requires a graph update. Transient issues (network lag, temporary UI glitches) should be retried, not recorded. Only update the graph for persistent structural changes.
