# Artifact Cleanup Plan

## Status: 2026-03-25

## Git Status

```
?? data/stress_test/
?? data/test_raw.bin
?? docs/RES-research/RES-adb-screencap-fps-analysis.md
?? docs/RES-research/RES-frame-ring-design.md
?? docs/decisions.md
?? docs/plans/adb-stress-test-plan.md
?? docs/plans/memu-transport-pipeline.md
?? docs/plans/steal-alas-device-module.md
?? docs/transport-methods.md
?? scripts/adb_stress_test.py
?? scripts/stress_test_adb.py
?? state_cartographer/base/
?? state_cartographer/transport/
```

## Categorization

### ✅ Commit These (Docs)

| File | Reason |
|------|--------|
| `docs/decisions.md` | Decision log — official record |
| `docs/plans/memu-transport-pipeline.md` | Active plan — primary reference |
| `docs/transport-methods.md` | Reference doc — single source of truth |
| `docs/RES-research/RES-adb-screencap-fps-analysis.md` | Research findings |
| `docs/RES-research/RES-frame-ring-design.md` | Research findings |

### ⚠️ Commit or Delete (Plans)

| File | Action |
|------|--------|
| `docs/plans/adb-stress-test-plan.md` | Superseded by `memu-transport-pipeline.md` — delete |
| `docs/plans/steal-alas-device-module.md` | Abandoned plan — delete |

### ❌ Delete (Artifacts & Scripts)

| File | Reason |
|------|--------|
| `scripts/adb_stress_test.py` | Duplicate of `stress_test_adb.py` |
| `data/stress_test/` | Test output — add to .gitignore |
| `data/test_raw.bin` | Debug artifact — add to .gitignore |

### ⚠️ Handle Carefully (ALAS Copies)

| File | Action |
|------|--------|
| `state_cartographer/base/` | Copied from ALAS, broken imports — needs cleanup or deletion |
| `state_cartographer/transport/` | Copied from ALAS, broken imports — needs cleanup or deletion |

The ALAS copies have 164 broken imports referencing `module.` paths. They should either be:
1. Deleted (we're not using them)
2. Or properly integrated (significant work)

**Recommendation: Delete both directories.** We have ALAS in `vendor/` if we need to reference it.

## Actions

### Immediate (Delete)

```bash
# Delete superseded plans
rm docs/plans/adb-stress-test-plan.md
rm docs/plans/steal-alas-device-module.md

# Delete duplicate script
rm scripts/adb_stress_test.py

# Delete ALAS copies (broken imports)
rm -rf state_cartographer/base/
rm -rf state_cartographer/transport/
```

### Add to .gitignore

```
# Stress test output
data/stress_test/
data/test_raw.bin

# ALAS copied modules (not used)
# state_cartographer/base/
# state_cartographer/transport/
```

### Commit Docs

```bash
git add docs/decisions.md
git add docs/plans/memu-transport-pipeline.md
git add docs/transport-methods.md
git add docs/RES-research/RES-*.md
git commit -m "docs: add transport pipeline plan, methods reference, and decisions log"
```

## Pre-commit Reminder

Run before committing:
- `uv run ruff check .`
- `uv run mypy state_cartographer/`

## See Also

- `docs/todo.md` — current state
- `docs/transport-methods.md` — capture/input methods reference
