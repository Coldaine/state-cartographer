# Session Notes — 2026-03-19

## Summary

DroidCast screenshot stability fixed via ATX agent restart trick. Live piloting captured Commission, HQ, and Dispatch screens. Redesign-plan.md vs MASTER_PLAN.md convergence confirmed — the gap at the planning level is closed.

---

## 1. Technical Work

### DroidCast Screenshot Stability — Root Cause & Fix

**Root cause:** MEmu uses DirectX rendering. DroidCast only returns 1 valid frame per process lifetime due to how it captures the DirectX framebuffer. Every subsequent frame is stale/black.

**Fix:** Restart DroidCast via the ATX agent HTTP endpoint before each screenshot capture.

- ATX agent exposes `POST /shell/background` on port 7912
- Port forwarding is now **fixed** (stable): `tcp:17912 -> tcp:7912` and `tcp:53516 -> tcp:53516`
- 3-second restart cycle, 100% reliable

**Files changed:**
- `scripts/pilot_bridge.py` — added `_restart_and_capture()` method using ATX agent (NOT simple `adb shell &`, which doesn't wait properly)
- `scripts/_droidcast_test.py` — new diagnostic tool for isolating DroidCast behavior

**ATX agent connection details:**
- Protocol: HTTP
- Device port: 7912
- Forwarded via: fixed local port `17912` (`adb forward tcp:17912 tcp:7912`)
- DroidCast forwarded via fixed local port `53516` (`adb forward tcp:53516 tcp:53516`)
- `pilot_bridge.connect()` now:
  1. Clears stale forwards for this device (`adb forward --remove-all`)
  2. Re-establishes exactly two fixed forwards (ATX and DroidCast)
  3. Verifies ATX agent is alive (GET `/info`)
  4. Performs a test capture
  5. Raises a meaningful `RuntimeError` with recovery instructions if ATX is not responding

---

## 2. Piloting Observations

Live screenshots captured via `pilot_bridge.py` during today's session.

### Main Page
- Commander: Kruzer Lv143
- Resources: Oil 9762, Gold 17338, Gems 4593

### HQ Page
Tabs/facilities visible:
- Academy, Dorm, Cat Lodge, Island Planner, Project Identity, Private Quarters

### Commission Panel (via `>>` expand on main page)
- COMPLETED: 1
- ONGOING: 1
- AVAILABLE: 2

### Commission Collect — "Frontier Defense Patrol"
Result: **WELL DONE S**

Ship EXP rewards (+2000 each):
- Nachi Lv62, Hiyou Lv63, Shirayuki Lv63, Vauquelin Lv63, Azusa Miura Lv64, Makinami Lv63

Item rewards:
- Cognitive Chips x20
- Oil x35
- **Commission Ticket x64 (EVENT item)**

### Commission List Screen
- Tab shown: Daily
- 4 commissions visible

### Dispatch Screen — "Daily Resource Extraction IV"
- Used **Recommend** button → 6 ships auto-filled
- Hit **Start**
- **Emulator crashed** mid-operation (MEmu main process died)

### Recovery
- Restarted MEmu emulator
- Relaunched Azur Lane
- Session ended at title screen (PRESS TO START)

---

## 3. Redesign Plan Analysis

### Finding: MASTER_PLAN.md and redesign-plan.md are CONVERGED

`docs/redesign-plan.md` was written as a diagnosis document ("we need to redesign from navigation library → automation runtime"). However, **`MASTER_PLAN.md` has already been updated to reflect the redesign.**

Evidence in `MASTER_PLAN.md`:
- Layer 5: Agent Supervision ✓
- Layer 4.5: Data Collection ✓
- Layer 4: Task Scheduler ✓
- Layer 3: Task Engine ✓

Scripts already in codebase:
- `task_model.py`, `scheduler.py`, `executor.py`, `resource_model.py` — listed as complete in Phase 3

**Conclusion:** The gap between the two documents is closed at the planning level. The redesign diagnosis was correct; the plan already reflects it.

### Key Remaining Gap

The automation loop doesn't drive **real gameplay** yet. Phase 4 piloting is the gateway — we're collecting action-sequence data (screenshots + tap coordinates) that will feed into concrete task definitions for the Layer 3-5 scripts.

---

## 4. ATX Agent Dependency

`pilot_bridge.py` now **requires** the ATX agent to be running on the device (port 7912).

### ATX Recovery Command (run after every emulator restart)

```powershell
# From the MasterStateMachine root:
vendor\AzurLaneAutoScript\.venv\Scripts\python.exe -c "import uiautomator2 as u2; u2.connect('127.0.0.1:21513')"
```

This auto-installs/recovers the ATX agent on the device. Wait for it to print a success message before calling `pilot_bridge.connect()`.

### What happens if you skip this

`pilot_bridge.connect()` will raise:
```
RuntimeError: ATX agent not responding on http://127.0.0.1:<port>. 
Run: vendor\AzurLaneAutoScript\.venv\Scripts\python.exe -c "import uiautomator2 as u2; u2.connect('127.0.0.1:21513')"
```

---

## 5. Part 2 — Live Piloting (Post-Restart, same session)

The session continued after the emulator restart. All screenshots at `data/screenshots/`.

### Navigation Path Recorded (in order)

| # | Screenshot | State (graph name) | Action taken |
|---|---|---|---|
| 1 | `post_restart_4.png` | `page_title` | Game loaded to PRESS TO START |
| 2 | `game_load_1.png` | _(no graph state)_ server select | Tapped start, saw Washington server select |
| 3 | `game_load_2.png` | loading/announcements | Waited for game to load |
| 4 | `after_announcement_close.png` | `page_announcement` or `page_event_list` | Closed patch note announcement → landed on Events menu |
| 5 | `main_page_after_restart.png` | `page_main` | Tapped home icon from events → main page |
| 6 | `wf_hq_entry.png` | `page_dormmenu` | Tapped HQ button (601,681); graph says (564,691) |
| 7 | `wf_dorm_entry.png` | `page_dorm` (entry popup) | Tapped DORM card → rest rewards popup (98:00:00 nap, 4338 EXP) |
| 8 | `wf_dorm_main.png` | `page_dorm` | Confirmed rest popup → Dorm interior (Rockstar 1F, Comfort 436, Train 6/6, Supplies 51986) |
| 9 | `wf_hq_after_dorm.png` | `page_main` | Pressed back (50,42) → exited to **main page directly** (skipped dormmenu) |
| 10 | `wf_hq_main.png` | `page_dormmenu` | Tapped HQ again → HQ page |
| 11 | `wf_cat_lodge_1.png` | `page_meowfficer` (entry popup) | Tapped CAT LODGE → meowfficer nap EXP popup (47040 EXP over 98h) |
| 12 | `wf_cat_lodge_2.png` | `page_meowfficer` | Confirmed EXP → Cattery main (75/75, grid of meowfficers) |
| 13 | `wf_cat_lodge_order.png` | `page_meowfficer` (Akashi Express sub) | Tapped Order slot (980,620) → Akashi Express opened |
| 14 | `wf_cat_lodge_order_result.png` | confirmation modal | "Your daily first Cat Box is free!" confirm dialog |
| 15 | `wf_cat_lodge_box_result.png` | item result modal | Got Rare Cat Box x1 |
| 16 | `wf_cat_lodge_after_box.png` | Akashi Express (post-free) | Free gone, next box 1200 coins |
| 17 | `wf_cat_lodge_3.png` | `page_meowfficer` | Pressed back → Cattery (Order now 14/15) |
| 18 | `wf_cat_lodge_trained.png` | `page_meowfficer` (Training popup) | Tapped Trained 10/10 → Training popup (4 slots all COMPLETE) |
| 19 | `wf_cat_lodge_finish_all.png` | same Training popup | Tapped Finish All — boxes still showing COMPLETE (needs investigation) |
| 20 | `wf_cat_lodge_box1.png` | same | Tapped first box individually — no change |
| 21 | `wf_cat_lodge_finish2.png` | same | Finish All again — still 4 COMPLETE |
| 22 | `wf_cat_lodge_finish3_immediate.png` | same | Fast screenshot after Finish All tap — **session ended here** |

### Commission Run (3/16 session)

Earlier session (3/16) captured the full commission flow:

| # | Screenshot | State | What happened |
|---|---|---|---|
| 1 | `main_page.png` | `page_main` | Main page baseline |
| 2 | `comm_01_after_left_tap.png` | `page_reward` | Tapped `>>` left panel (20,164?) |
| 3 | `comm_02_expand_left.png` | `page_reward` | Left panel expanded |
| 4 | `comm_03_complete.png` | `page_reward` | Commission COMPLETED shown |
| 5 | `comm_04_dismiss.png` | `page_reward` | Dismissing complete notification |
| 6 | `comm_05_continue.png` | `page_reward` | Collection flow |
| 7 | `comm_06_list.png` | `page_commission` | Full commission list page |
| 8 | `comm_07_dispatch.png` | `page_commission` | Dispatch detail for new commission |
| 9 | `comm_08_select.png` | `page_commission` | Ship select panel |
| 10 | `comm_09_recommend.png` | `page_commission` | Hit Recommend → 6 ships auto-filled |
| 11 | `comm_10_started.png` | `page_commission` | Hit Start — emulator crashed here |

---

## 6. State Machine vs Live Observation — One-to-One Match

### States CONFIRMED by live screenshots

| Graph State | Observed? | Notes |
|---|---|---|
| `page_main` | ✅ Yes | `main_page_after_restart.png`, `wf_hq_after_dorm.png` — confirmed nav bar, resources |
| `page_dormmenu` | ✅ Yes | `wf_hq_entry.png`, `wf_hq_main.png` — in-game label is "HQ", shows facility cards |
| `page_dorm` | ✅ Yes | `wf_dorm_entry.png`, `wf_dorm_main.png` — Dorm interior, supplies timer |
| `page_meowfficer` | ✅ Yes | `wf_cat_lodge_1.png` through `wf_cat_lodge_finish3_immediate.png` — Cat Lodge/Cattery |
| `page_title` | ✅ Yes | `post_restart_4.png` — PRESS TO START, ver 9.2.493 |
| `page_announcement` | ✅ Yes | Announcement closed at (1205, 93) — graph anchor close tap (1203, 91) ✅ near-match |
| `page_commission` | ✅ Yes | `comm_06_list.png` through `comm_10_started.png` |
| `page_reward` | ✅ Yes (inferred) | `comm_01` through `comm_05` — left expandable panel is page_reward in ALAS |
| `page_event_list` | ✅ Likely | `after_announcement_close.png` — Events side menu appeared after announcement dismiss |

### Transition Coordinate Comparison (graph vs live taps)

| Transition | Graph coords | Live tap coords | Delta | Match? |
|---|---|---|---|---|
| `main_to_dormmenu` | (564, 691) | (601, 681) | 37px X, 10px Y | ⚠️ Off — HQ button is at ~601 |
| `dormmenu_to_dorm` | (474, 540) | (429, 480) | 45px X, 60px Y | ⚠️ Off — card center differs |
| `dormmenu_to_meowfficer` | (691, 540) | (660, 480) | 31px X, 60px Y | ⚠️ Off — consistent Y error |
| `dorm_to_main` | (51, 45) | (50, 42) | 1px X, 3px Y | ✅ Exact match |
| `page_announcement` X-close | (1203, 91) | (1205, 93) | 2px X, 2px Y | ✅ Exact match |

**Pattern**: The dormmenu card taps are all off by ~30–45px X and ~60px Y. This suggests the ALAS-derived coordinates for the HQ sub-cards are from a different UI layout or resolution mapping. The back/close button coordinates are accurate.

### States in Graph NOT YET OBSERVED

All combat-related states (campaign, exercise, OS, etc.) plus: shop, dock, build, guild, research, shipyard, academy. These have never been screenshot-confirmed.

### States OBSERVED but MISSING from Graph

| Observed screen | Notes |
|---|---|
| Server selection screen | Between `page_title` and `page_main` — not modeled |
| Dorm rest-up popup | Transient modal when entering dorm with completed rest timer |
| Cat Lodge EXP collection popup | Transient modal when entering Cat Lodge with nap complete |
| Akashi Express order page | Sub-page within meowfficer — daily free cat box ordering |
| Item Found result modal | Transient modal after cat box purchase |
| Cat Lodge Training popup | Sub-page within meowfficer — 4 training slots |
| Island Planner | Card visible on `page_dormmenu` but no `dormmenu_to_island_planner` transition |
| Project Identity | Card on `page_dormmenu` but no `dormmenu_to_project_identity` transition |

### Transitions MISSING from Graph

| Missing transition | Evidence |
|---|---|
| `page_announcement` → `page_event_list` (or similar) | After closing announcement, game showed Events screen |
| `dormmenu_to_island_planner` | Island Planner card visible on HQ page |
| `dormmenu_to_project_identity` | Project Identity card visible on HQ page |
| `dorm_to_dormmenu` | Back arrow from dorm actually exits to `page_main` — `dorm_to_main` is correct, no dormmenu intermediate |
| `meowfficer_to_dormmenu` | Back arrow from Cat Lodge likely returns to `page_dormmenu`, but graph only has `meowfficer_to_main` — **may be wrong** |

---

## 7. TODO / Pending Work

### High Priority

- [ ] **Auto-recover ATX agent in `pilot_bridge.connect()`** — instead of raising immediately, detect ATX not responding, run `u2.connect()` recovery automatically, retry once
- [ ] **Cat Lodge Training "Finish All"** — understand why Finish All wasn't collecting the 4 COMPLETE boxes; try longer wait or different tap target
- [ ] **Fix dormmenu card coordinates** — all HQ sub-card taps are off by ~30–60px. Need to live-verify each card center and update graph transitions.
- [ ] **Verify `meowfficer_to_dormmenu`** — back arrow from Cat Lodge goes to HQ or main? Graph currently says main; may need updating.
- [ ] **Confirm `page_event_list` anchor** — screenshot after announcement close shows events menu; need pixel sample to confirm it's `page_event_list` and add `announcement → event_list` transition.

### Medium Priority

- [ ] **Emulator crash reproducibility** — did the dispatch tap cause the crash? Add crash detection in `pilot_bridge` (process health check)
- [ ] **Anchor candidacy review** — review today's screenshots for stable pixel anchors for: main page, HQ page, commission panel, commission list, dispatch screen
- [ ] **`_droidcast_test.py` integration** — wire it into CI or make it a runnable dev sanity check

### Lower Priority

- [ ] Close out `redesign-plan.md` as "superseded by MASTER_PLAN.md" (add a header note, no content changes needed)
- [ ] Add "Daily Resource Extraction IV" as a concrete example workflow in `docs/workflows.md`

---

## 8. New Discovery — ADB Forward Saturation (Why screenshots went black intermittently)

### Symptom
- Emulator visibly showed the game/login menu.
- Captures sometimes came back black in both pilot flow and ad-hoc checks.

### Root Cause
- `pilot_bridge` previously requested **ephemeral local forwards** on each connect/capture (`adb forward tcp:0 ...`).
- Over time this accumulated dozens of stale forward entries (44 observed in one run).
- Multiple stale forwards did not always break ATX itself, but introduced inconsistent routing/state across repeated capture attempts.

### Confirmed Fix
- Switched to a stable two-forward model:
  - `tcp:17912 -> tcp:7912` (ATX)
  - `tcp:53516 -> tcp:53516` (DroidCast)
- `connect()` now starts from a clean slate by removing stale forwards for the device.
- Validation run: 3 consecutive screenshots succeeded; forward list stayed at exactly 2 entries.

### Evidence Snapshot
- `adb -s 127.0.0.1:21513 forward --list` after validation:
  - `127.0.0.1:21513 tcp:17912 tcp:7912`
  - `127.0.0.1:21513 tcp:53516 tcp:53516`

## Session Environment

| Item | Value |
|------|-------|
| Emulator | MEmu, `127.0.0.1:21513` |
| Game | Azur Lane EN (`com.YoStarEN.AzurLane`) |
| ATX agent port | 7912 (forwarded locally as `tcp:17912`) |
| DroidCast local forward | `tcp:53516` |
| DroidCast restart cycle | ~3 seconds |
| ALAS config | `PatrickCustom` |
