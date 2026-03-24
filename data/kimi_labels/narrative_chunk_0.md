# Azur Lane Gameplay Session - Narrative Summary

**Date:** 2026-03-20  
**Session Time Range:** 00:22:41 - 00:58:50  
**Total Frames Processed:** 467  
**ALAS Log Start:** 00:26:45  

---

## Session Overview

This dataset captures an Azur Lane gameplay session spanning approximately 36 minutes. The first ~4 minutes (frames 1-116) predate the ALAS automation session and represent manual gameplay or idle time. From 00:26:45 onwards, ALAS (AzurLaneAutoScript) automation took over, executing a series of scheduled tasks.

---

## Phase 1: Pre-ALAS Activity (00:22:41 - 00:26:45)

**Frames:** 20260320_002241_384 through approximately 20260320_002643_xxx (116 frames)

### Key Events:
- **00:22:41** - Network connection error dialog appears ("Reconnect now? [ConnectionReset]")
- **00:22:43** - Game map view: NA Ocean NE Sector C - Safe Zone with fleet formation
- **00:22:48** - Main menu (page_main) with character Kruzer (Level 143)
- **00:22:49** - Reward page (page_reward) showing active commissions and tactical classes
- **00:22:55** - Commission page - Daily tab showing 4 ongoing oil extraction and defense missions
- **00:22:56** - Commission page - Urgent tab showing limited-time missions
- **00:23:09** - Network connection error dialog reappears
- **00:23:31** - Tactical Class page showing 4 shipgirls in training (Moskva, Gorizia, Allen M. Sumner, Owari)
- **00:23:44** - Return to main screen
- **00:23:46** - Technology menu navigation
- **00:23:48** - Research Academy showing 5 active/queued projects
- **00:23:50** - Research details showing O-478-RF complete, ready to claim
- **00:23:53** - Item found dialog: Blueprint - Prinz Rupprecht + equipment rewards

### Pre-ALAS Summary:
The player was managing commissions, research projects, and dealing with intermittent network connectivity issues. Several daily missions were already in progress, and one research project was completed and claimed.

---

## Phase 2: ALAS Commission Task (00:26:45 - 00:27:35)

**ALAS Task:** Commission  
**Page Flow:** page_main → page_reward → page_commission → page_reward

### Key Actions:
1. **00:26:51** - ALAS initializes: "UI get current page"
2. **00:26:55** - Detected at page_main
3. **00:26:55** - Navigation: "Goto page_reward" 
4. **00:26:58** - Arrived at page_reward, clicked REWARD_GOTO_COMMISSION
5. **00:27:00** - Clicked COMMISSION_URGENT tab
6. **00:27:03** - Clicked COMMISSION_DAILY tab
7. **00:27:07** - Clicked COMMISSION_URGENT tab again
8. **00:27:10** - Commission scan detected: NYB Gear Research (running), Large-scale Oil Extraction (running), Buoy Inspection (pending), Large Merchant Escort (pending)
9. **00:27:32** - Commission task completed, scheduled next run for 05:53:35

### Commission Task Summary:
ALAS scanned both daily and urgent commissions, confirmed all available missions were either running or would exceed time limits, and deferred the task.

---

## Phase 3: ALAS Tactical Task (00:27:35 - 00:27:42)

**ALAS Task:** Tactical  
**Page Flow:** page_reward → page_tactical → page_reward

### Key Actions:
1. **00:27:35** - Clicked REWARD_GOTO_TACTICAL
2. **00:27:39** - Tactical class page loaded, 4 shipgirls in training
3. **00:27:39** - Back arrow clicked, returned to reward page

### Tactical Task Summary:
ALAS verified all 4 tactical class slots were occupied with ongoing training (Moskva, Gorizia, Allen M. Sumner, Owari with 7+ hours remaining each).

---

## Phase 4: ALAS Research Task (00:27:42 - 00:28:09)

**ALAS Task:** Research  
**Page Flow:** page_reward → page_main → page_reshmenu → page_research

### Key Actions:
1. **00:27:42** - Navigation: "Goto page_research"
2. **00:27:44** - Clicked MAIN_GOTO_RESHMENU
3. **00:27:47** - Clicked RESHMENU_GOTO_RESEARCH
4. **00:27:49** - Arrived at page_research
5. **00:27:49** - Clicked RESEARCH_GOTO_QUEUE
6. **00:27:51** - Back arrow clicked

### Research Task Summary:
ALAS checked research queue, confirmed all slots were filled with projects in various stages.

---

## Phase 5: ALAS Dorm Task (00:28:09 - 00:28:21)

**ALAS Task:** Dorm  
**Page Flow:** page_research → page_main → page_dormmenu → page_dorm

### Key Actions:
1. **00:28:09** - Navigation: "Goto page_dormmenu"
2. **00:28:11** - Clicked MAIN_GOTO_DORMMENU_WHITE
3. **00:28:13** - Arrived at page_dormmenu
4. **00:28:13** - Clicked DORMMENU_GOTO_DORM
5. **00:28:18** - Clicked DORM_INFO
6. **00:28:20** - Clicked DORM_FEED_ENTER

### Dorm Task Summary:
ALAS managed dormitory functions, likely refilling food or interacting with shipgirls.

---

## Phase 6: ALAS Meowfficer Task (00:28:21 - 00:28:38)

**ALAS Task:** Meowfficer  
**Page Flow:** page_dorm → page_dormmenu → page_meowfficer

### Key Actions:
1. **00:28:21** - Clicked DORMMENU_GOTO_MEOWFFICER
2. **00:28:23** - Arrived at page_meowfficer
3. **00:28:27** - Meowfficer training check completed

### Meowfficer Task Summary:
ALAS checked Meowfficer (cat companion) training status.

---

## Phase 7: ALAS Guild Task (00:37:44 - 00:38:10)

**ALAS Task:** Guild  
**Page Flow:** page_exercise → page_guild

### Key Actions:
1. **00:37:44** - Transition from Exercise to Guild
2. **00:37:59** - Clicked MAIN_GOTO_GUILD_WHITE
3. **00:38:01** - Arrived at page_guild

### Guild Task Summary:
ALAS visited the guild page, likely to collect daily rewards or check guild operations.

---

## Phase 8: ALAS Reward Task (00:44:13 - 00:44:32)

**ALAS Task:** Reward  
**Page Flow:** page_main → page_reward → page_main

### Key Actions:
1. **00:44:13** - Navigation: "Goto page_reward"
2. **00:44:20** - Arrived at page_reward
3. **00:44:24** - Clicked REWARD_GOTO_COMMISSION
4. **00:44:32** - Clicked BACK_ARROW

### Reward Task Summary:
ALAS collected reward items and checked commission status.

---

## Phase 9: ALAS Freebies Task (00:58:20 - 00:58:50)

**ALAS Task:** Freebies  
**Page Flow:** page_main → page_shop

### Key Actions:
1. **00:58:20** - Clicked GOTO_MAIN_WHITE
2. **00:58:33** - Clicked POPUP_CONFIRM_WHITE_MAIL_CLAIM
3. **00:58:49** - Clicked SUPPLY_PACK_CHECK
4. **00:58:50** - At page_shop, final frame in dataset

### Freebies Task Summary:
ALAS collected free daily items from the shop and mail system.

---

## Data Statistics

| Metric | Count |
|--------|-------|
| Total Frames | 467 |
| Pre-ALAS Frames | ~116 (24.8%) |
| During ALAS Frames | ~351 (75.2%) |
| Unique ALAS Tasks | 9 (Commission, Tactical, Research, Dorm, Meowfficer, Guild, Reward, Freebies, Exercise) |
| Distinct Page States | 15+ |
| Network Error Dialogs | 2 |
| Item Claim Events | 1 (Research rewards) |

---

## Label Schema

Each frame in `correlated_chunk_0.jsonl` contains:
- `filename`: Screenshot filename
- `timestamp`: HH:MM:SS.mmm format
- `page`: Detected game page (from ALAS log correlation)
- `alas_task`: Active ALAS task at this time
- `alas_action`: Specific ALAS button/action
- `visual_description`: Manual description (for key frames)
- `note`: Context note (Pre-ALAS vs During ALAS)

---

## Notes for ML Training

1. **Page Classification**: The dataset covers 15+ distinct game pages, good for training page detection models
2. **Temporal Consistency**: Frames are chronologically ordered with ~3-10 second intervals
3. **ALAS Correlation**: ~75% of frames have direct ALAS log correlation for supervised learning
4. **Error States**: Network error dialogs present for anomaly detection training
5. **Transition States**: Multiple loading/transition frames between pages
6. **Task Diversity**: Covers the main Azur Lane daily loop tasks

---

*Generated from ALAS log correlation and manual frame inspection*
