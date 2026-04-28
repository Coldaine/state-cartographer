# Azur Lane Navigation State Machine Extraction

Extracted from ALAS (AzurLaneAutoScript) codebase, April 2026.
Base resolution: **1280x720**. All coordinates are (x1, y1, x2, y2) bounding boxes.
Region: EN (english client). CN/JP/TW coordinates differ slightly.

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

The campaign menu has specific click zones for each destination:

| Button | Detection Area | Click Area | Destination |
|--------|---------------|------------|-------------|
| CAMPAIGN_MENU_GOTO_CAMPAIGN | (374, 449, 503, 483) | (170, 119, 509, 553) | Main Campaign (left card) |
| CAMPAIGN_MENU_GOTO_EVENT | (374, 449, 503, 483) | (544, 120, 966, 325) | Event (top-right card) |
| CAMPAIGN_MENU_GOTO_OS | (374, 449, 503, 483) | (543, 345, 967, 552) | Operation Siren (bottom-right card) |
| CAMPAIGN_MENU_GOTO_EXERCISE | (1010, 600, 1102, 624) | (1010, 600, 1102, 624) | Exercises (bottom bar) |
| CAMPAIGN_MENU_GOTO_DAILY | (729, 590, 784, 635) | (729, 590, 784, 635) | Daily Raids (bottom bar) |
| CAMPAIGN_MENU_GOTO_WAR_ARCHIVES | (222, 590, 308, 634) | (222, 590, 308, 634) | War Archives (bottom bar) |

**Note:** CAMPAIGN_MENU_GOTO_EVENT is polymorphic — the same click area leads to
different screens depending on the active event (page_event, page_sp, page_coalition,
page_raid, page_rpg_stage, page_hospital). All share detection area but land on
different pages. Determine which event is active after clicking.

## Screen Identification (check_button areas, EN)

Each screen has a distinctive region to template-match:

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

## Key Observations

1. **Back button is nearly universal at top-left (~40, 45)** — same spot on campaign menu,
   exercise, daily, commission, guild, research, shop, etc.

2. **Home button is nearly universal at top-right (~1235, 35)** — works from almost
   every screen to jump directly to main.

3. **The bottom nav bar (SHOP/DOCK/DEPOT/HQ/LAB/MISSIONS/BUILD/GUILD)** only appears
   on page_main (white UI). It disappears on all sub-screens.

4. **Campaign menu is visually distinct** — "Attack" header, two large cards
   (Main Campaign + current event/OpSi), bottom bar with War Archives/Challenge
   Mode/Daily Raids/Commissions/Exercises.

5. **Transitions take ~1-2 seconds** — based on log timestamp analysis, screen switches
   complete within 1-2 seconds of the click.

6. **ALAS screenshot interval**: 0.3s during fast operations, 1.0s during loading.

## Source Files

- `module/ui/page.py` — Page definitions and .link() graph (356 lines)
- `module/ui/assets.py` — Button coordinates (95 buttons)
- `module/ui_white/assets.py` — White UI button coordinates (35 buttons)
- `module/ui/ui.py` — Navigation engine (ui_goto, ui_get_current_page, ui_additional)
- `module/base/button.py` — Button template matching implementation
