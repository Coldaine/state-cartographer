# ALAS Navigation State Machine

Extracted from ALAS (AzurLaneAutoScript) codebase at `D:\_projects\ALAS_original`, April 2026.
Base resolution: **1280x720**. All coordinates are (x1, y1, x2, y2) bounding boxes.
Region: EN (english client). CN/JP/TW coordinates differ slightly.

Source: `module/ui/page.py` (357 lines), `module/ui/ui.py` (640 lines)

## Universal Navigation Buttons

Two buttons appear on nearly every screen:

| Button | Detection Area (EN) | Click Area (EN) | Action |
|--------|-------------------|-----------------|--------|
| **Back (top-left)** | (33, 44, 47, 64) | (33, 31, 81, 78) | Go back one level |
| **Home (top-right)** | (1217, 23, 1241, 45) | (1213, 18, 1245, 49) | Jump to main screen |

**Exceptions** (screens with non-standard back/home positions):
- `page_reward`: REWARD_GOTO_MAIN detects at (219, 107, 267, 158), clicks at (787, 602, 867, 642)
- `page_private_quarters`: PQ_GOTO_MAIN at (1107, 19, 1143, 51)
- `page_game_room`: GAME_ROOM_GOTO_MAIN at (1210, 16, 1247, 51)
- `page_dorm`: DORM_GOTO_MAIN at (40, 30, 62, 60) — same zone, slightly different
- `page_dormmenu`: DORMMENU_GOTO_MAIN detects (261, 487, 334, 587), clicks (150, 153, 437, 279)

## Navigation Strategy

Max depth from main is 3. Every page has a home button. So:

```
goto(target):
    if at(target): return
    if not at(main): click HOME (top-right)
    for button in ROUTES[target]:
        click(button)
        wait_for_transition()
```

## Route Table (main -> target)

Each entry is an ordered list of clicks from page_main.

### Depth 1 (one click from main)
| Target | Button | Click Area (EN) |
|--------|--------|-----------------|
| page_campaign_menu | MAIN_GOTO_CAMPAIGN_WHITE | (1043, 640, 1244, 700) |
| page_fleet | MAIN_GOTO_FLEET_WHITE | (varies) |
| page_reward | MAIN_GOTO_REWARD_WHITE | (11, 209, 30, 259) |
| page_mission | MAIN_GOTO_MISSION_WHITE | (802, 656, 949, 704) |
| page_guild | MAIN_GOTO_GUILD_WHITE | (1116, 656, 1261, 703) |
| page_dock | MAIN_GOTO_DOCK_WHITE | (176, 656, 322, 703) |
| page_storage | MAIN_GOTO_STORAGE_WHITE | (331, 656, 478, 703) |
| page_reshmenu | MAIN_GOTO_RESHMENU_WHITE | (646, 656, 793, 703) |
| page_dormmenu | MAIN_GOTO_DORMMENU_WHITE | (490, 656, 634, 702) |
| page_shop | MAIN_GOTO_SHOP_WHITE | (18, 656, 164, 703) |
| page_build | MAIN_GOTO_BUILD | (958, 665, 1113, 714) |
| page_event_list | MAIN_GOTO_EVENT_LIST_WHITE | (1181, 83, 1260, 160) |
| page_mail | MAIL_ENTER_WHITE | (1018, 22, 1087, 52) |

### Depth 2 (main -> submenu -> target)
| Target | Step 1 | Step 2 |
|--------|--------|--------|
| page_campaign | MAIN_GOTO_CAMPAIGN_WHITE -> | CAMPAIGN_MENU_GOTO_CAMPAIGN |
| page_exercise | MAIN_GOTO_CAMPAIGN_WHITE -> | CAMPAIGN_MENU_GOTO_EXERCISE |
| page_daily | MAIN_GOTO_CAMPAIGN_WHITE -> | CAMPAIGN_MENU_GOTO_DAILY |
| page_event (varies) | MAIN_GOTO_CAMPAIGN_WHITE -> | CAMPAIGN_MENU_GOTO_EVENT |
| page_os | MAIN_GOTO_CAMPAIGN_WHITE -> | CAMPAIGN_MENU_GOTO_OS |
| page_archives | MAIN_GOTO_CAMPAIGN_WHITE -> | CAMPAIGN_MENU_GOTO_WAR_ARCHIVES |
| page_commission | MAIN_GOTO_REWARD_WHITE -> | REWARD_GOTO_COMMISSION |
| page_tactical | MAIN_GOTO_REWARD_WHITE -> | REWARD_GOTO_TACTICAL |
| page_battle_pass | MAIN_GOTO_REWARD_WHITE -> | REWARD_GOTO_BATTLE_PASS |
| page_research | MAIN_GOTO_RESHMENU_WHITE -> | RESHMENU_GOTO_RESEARCH |
| page_shipyard | MAIN_GOTO_RESHMENU_WHITE -> | RESHMENU_GOTO_SHIPYARD |
| page_meta | MAIN_GOTO_RESHMENU_WHITE -> | RESHMENU_GOTO_META |
| page_dorm | MAIN_GOTO_DORMMENU_WHITE -> | DORMMENU_GOTO_DORM |
| page_meowfficer | MAIN_GOTO_DORMMENU_WHITE -> | DORMMENU_GOTO_MEOWFFICER |
| page_academy | MAIN_GOTO_DORMMENU_WHITE -> | DORMMENU_GOTO_ACADEMY |
| page_private_quarters | MAIN_GOTO_DORMMENU_WHITE -> | DORMMENU_GOTO_PRIVATE_QUARTERS |
| page_supply_pack | MAIN_GOTO_SHOP_WHITE -> | SHOP_GOTO_SUPPLY_PACK |
| page_munitions | MAIN_GOTO_SHOP_WHITE -> | SHOP_GOTO_MUNITIONS |

### Depth 3 (main -> submenu -> submenu -> target)
| Target | Step 1 | Step 2 | Step 3 |
|--------|--------|--------|--------|
| page_game_room | MAIN_GOTO_DORMMENU_WHITE -> | DORMMENU_GOTO_ACADEMY -> | ACADEMY_GOTO_GAME_ROOM |
| page_munitions (alt) | MAIN_GOTO_DORMMENU_WHITE -> | DORMMENU_GOTO_ACADEMY -> | ACADEMY_GOTO_MUNITIONS |

## Campaign Menu Click Areas (EN)

| Button | Detection Area | Click Area | Destination |
|--------|---------------|------------|-------------|
| CAMPAIGN_MENU_GOTO_CAMPAIGN | (374, 449, 503, 483) | (170, 119, 509, 553) | Main Campaign (left card) |
| CAMPAIGN_MENU_GOTO_EVENT | (374, 449, 503, 483) | (544, 120, 966, 325) | Event (top-right card) |
| CAMPAIGN_MENU_GOTO_OS | (374, 449, 503, 483) | (543, 345, 967, 552) | Operation Siren (bottom-right card) |
| CAMPAIGN_MENU_GOTO_EXERCISE | (1010, 600, 1102, 624) | (1010, 600, 1102, 624) | Exercises (bottom bar) |
| CAMPAIGN_MENU_GOTO_DAILY | (729, 590, 784, 635) | (729, 590, 784, 635) | Daily Raids (bottom bar) |
| CAMPAIGN_MENU_GOTO_WAR_ARCHIVES | (222, 590, 308, 634) | (222, 590, 308, 634) | War Archives (bottom bar) |

**Event polymorphism:** CAMPAIGN_MENU_GOTO_EVENT is polymorphic — the same click area leads to different screens depending on the active event (page_event, page_sp, page_coalition, page_raid, page_rpg_stage, page_hospital). All share the detection area but land on different pages. The active event determines which page appears.

## Screen Identification (check_button areas, EN)

Each screen has a distinctive region to template-match (ALAS method — the VLM replaces this with button inventory observation):

| Page | Check Button | Detection Area (EN) |
|------|-------------|-------------------|
| page_main | MAIN_GOTO_FLEET | (1043, 640, 1244, 700) |
| page_main_white | MAIN_GOTO_CAMPAIGN_WHITE | (varies) |
| page_campaign_menu | CAMPAIGN_MENU_CHECK | (374, 449, 503, 483) |
| page_campaign | CAMPAIGN_CHECK | (varies) |
| page_fleet | FLEET_CHECK | (1043, 640, 1244, 700) |
| page_exercise | EXERCISE_CHECK | (varies) |
| page_daily | DAILY_CHECK | (23, 656, 67, 698) |
| page_os | OS_CHECK | (613, 17, 627, 34) |
| page_reward | REWARD_CHECK | (varies) |
| page_commission | COMMISSION_CHECK | (120, 14, 301, 41) |
| page_guild | GUILD_CHECK | (121, 15, 196, 39) |
| page_research | RESEARCH_CHECK | (varies) |
| page_shop | SHOP_CHECK | (143, 25, 199, 41) |
| page_dorm | DORM_CHECK | (949, 600, 1005, 654) |
| page_dormmenu | DORMMENU_CHECK | (261, 487, 334, 587) |

**Note:** page_main and page_main_white are the same logical screen with different UI themes. They have different button sets available (different `.link()` targets in ALAS). ALAS handles this with special-case logic in `ui_page_appear()`.

## Ephemeral Popups

True popups are brief overlays that appear on top of whatever page you're on. They interrupt navigation and need dismissing. Once dismissed, you're back on the page you were on. They are NOT full screens — they overlay the current screen.

Common triggers:
- **Login/daily reset**: Announcements, return bonuses, "what's new" notices
- **Reward collection**: Items received, ships acquired — often "tap anywhere to continue"
- **Expiry notices**: Monthly pass, battle pass, item expiration warnings
- **Connection issues**: Disconnected, poor connection — asks to retry or exit
- **Story/cutscene**: Plays automatically, needs skip button
- **Idle timeout**: Screen dims after inactivity, tap anywhere to resume
- **Maintenance**: Server going down, dismissible notice

These are handled differently from full screens because:
- They can appear at any time on any page
- Dismissing them returns to the previous state (no navigation change)
- Some have a dismiss button, some are "tap anywhere to continue"
- New ones appear with game updates — the list is never complete

**For the VLM runtime:** The VLM will see these as unexpected overlays in the button inventory. The correct action is usually to dismiss (tap a button, tap anywhere, or skip). The VLM can reason about novel popups it hasn't seen before — this is the advantage over ALAS's hardcoded popup handlers. Connection error dialogs may require a choice (retry vs exit) based on the runtime's recovery strategy.

**ALAS reference:** These are handled in `ui_additional()`, `ui_page_main_popups()`, `ui_page_os_popups()`, and `handle_idle_page()` in `module/ui/ui.py`. ALAS handles ~30 specific popup types via template matching. The VLM replaces this with general visual understanding.

## Screens ALAS Treats as Navigation Interruptions

These are NOT popups — they are full screens with their own UI. ALAS handles them in `ui_additional()` because they can be reached accidentally during navigation (wrong click), but they are real pages. In the VLM runtime, these are just regular screens the VLM observes normally.

Examples:
- Fleet preparation (accidentally entered a stage)
- Exercise preparation (accidentally entered exercise)
- Dorm feed screen
- Exchange shop (OpSi)
- Research project selection
- Meowfficer purchase screen

ALAS's `ui_additional()` backs out of these during navigation because they weren't the intended destination. In the VLM runtime, the VLM sees the screen, recognizes it's not the target, and the graph routes back (usually via BACK or HOME).

## Key Observations

1. **Back button is nearly universal at top-left (~40, 45)** — same spot on campaign menu, exercise, daily, commission, guild, research, shop, etc.

2. **Home button is nearly universal at top-right (~1235, 35)** — works from almost every screen to jump directly to main.

3. **The bottom nav bar (SHOP/DOCK/DEPOT/HQ/LAB/MISSIONS/BUILD/GUILD)** only appears on page_main (white UI). It disappears on all sub-screens.

4. **Campaign menu is visually distinct** — "Attack" header, two large cards (Main Campaign + current event/OpSi), bottom bar with War Archives/Challenge Mode/Daily Raids/Commissions/Exercises.

5. **Transitions take ~1-2 seconds** — screen switches complete within 1-2 seconds of the click.

6. **ALAS screenshot interval**: 0.3s during fast operations, 1.0s during loading.

## Dock Substates (State Cartographer additions)

These substates are not present in ALAS (ALAS treats the dock as a flat page). They are defined by the State Cartographer project for data collection workflows.

### Dock Grid View (`page_dock_grid`)
The main dock screen is a scrollable grid of ship cards. This is the default view when entering `page_dock`.

**Navigation:** This IS `page_dock` — entering the dock always lands here.

### Ship Detail View (`page_ship_detail`)
Tapping any ship card in the grid opens the detail view.

**Entry:** Tap a ship card in `page_dock_grid`
**Exit:** Tap back button (57, 55) → returns to `page_dock_grid`
**Contains:** Ship name, level, rarity, affinity, stats, skills, limit break stars

### Ship Gear View (`page_ship_gear`)
The equipment/gear tab within the ship detail view.

**Entry:** Tap gear tab (~980, 140) from `page_ship_detail`
**Exit:** Tap back button (57, 55) → returns to `page_dock_grid` (not ship detail)
**Contains:** All equipment slots visible in a single view (5 gear + 1 augment)

### Dock Sort/Filter (`page_dock_sort`)
Sort and filter controls that overlay the dock grid.

**Entry:** Tap sort/filter button on `page_dock_grid`
**Exit:** Select sort option or tap outside → returns to `page_dock_grid`

### Route Table (Dock substates)

| From | Action | To |
|------|--------|----|
| page_dock_grid | Tap ship card | page_ship_detail |
| page_ship_detail | Tap gear tab | page_ship_gear |
| page_ship_detail | Tap back (57, 55) | page_dock_grid |
| page_ship_gear | Tap back (57, 55) | page_dock_grid |
| page_dock_grid | Tap sort button | page_dock_sort |
| page_dock_sort | Select/dismiss | page_dock_grid |

## Source Files (in ALAS_original)

- `module/ui/page.py` — Page definitions and .link() graph (357 lines)
- `module/ui/assets.py` — Button coordinates (95 buttons)
- `module/ui_white/assets.py` — White UI button coordinates (35 buttons)
- `module/ui/ui.py` — Navigation engine (ui_goto, ui_get_current_page, ui_additional)
- `module/base/button.py` — Button template matching implementation
