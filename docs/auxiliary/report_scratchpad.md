# ALAS Configuration Review & Optimization Scratchpad

## Game Overview: Azur Lane Endgame Focus
For an endgame player, the goal of ALAS is to manage tedious resource grinds while protecting key bottlenecks: **Cognitive Arrays, Gold Plates, Coins, and efficient Oil-to-EXP conversions**. 

---

## 1. Research Lab Priorities & Management
*   **Current State:** You have completed all PR/DR ship developments and are focused exclusively on farming the **PR5 152mm (Rainbow) Gun** (`series_5_152_only`). 
*   **Optimization/Tweaks (Coins & Cubes):** 
    *   Cubes are successfully blocked (`UseCube: do_not_use`).
    *   To strictly preserve Coins, you must modify your Research logic to prioritize free or alternative-cost projects.
    *   **Actionable Change:** Move away from pure coin-based researches. Update your Custom Filter to prioritize **Q (Scrapping/Disassembly)**, **G (Commission/Grant)**, and **C (Specific Ship EXP/Completion)** series researches for the S5-152 gun before falling back on coin-heavy (D/E/H) projects. 

## 2. Operation Siren (OpSi) Monthly Logic & The Missing Link
You are completely correct to call me out. OpSi resets every month, and ALAS has a highly specific, hardcoded priority list that perfectly explains why `OpsiExplore` was running and why it suppressed your AP burn.

### The ALAS OpSi Loop (Mentally Walked Through)
Here is the exact priority and gating logic ALAS uses for Operation Siren:

1.  **The Start of Month Gate (`OpsiExplore`):**
    When the month resets, the map goes dark. `OpsiExplore` wakes up. Its job is to unlock the entire map. While it does this, it acts as a **Gatekeeper**. The code literally reads: *"Delay other OpSi tasks during OpsiExplore"*. It pushes `Abyssal`, `Stronghold`, and `MeowfficerFarming` an hour into the future every time it runs. It does this so you don't waste AP fighting bosses in uncleared zones.
    *   **The Timer:** Once `OpsiExplore` reaches the final zone, it detects completion, shuts down, and sets its timer to **the 1st of the next month**.

2.  **The Daily Maintenance (High Priority):**
    With the map cleared, the daily priority is: `OpsiAshBeacon` -> `OpsiDaily` -> `OpsiShop`. These run first because they are time-sensitive or take zero AP.

3.  **The Boss Hierarchy (Mid Priority):**
    If dailies are done, the bot tackles bosses in this exact order: 
    **`Abyssal`** (Highest) -> **`Stronghold`** -> **`Obscure`** -> `MonthBoss`. 
    *   *Note on the previous `ForceRun` bug:* As established, `Abyssal` and `Stronghold` currently ignore their `SuccessInterval` and force a chain-run, then lock themselves out until tomorrow.

4.  **The "AP Burn" Sinkhole (Lowest Priority):**
    **`OpsiMeowfficerFarming`** is the absolute lowest priority task in ALAS (lower than main campaign, events, and dorms). It is the designated AP dump. 

### Why you ended the season with 3,000 AP
Because `MeowfficerFarming` is at the absolute bottom of the `SCHEDULER_PRIORITY` list, it is incredibly fragile. 
If your bot is busy running the Event, doing Dailies, or checking the Shop, `MeowfficerFarming` gets skipped. Even when it finally gets a chance to run, if you leave its `SuccessInterval` too high (e.g., 30 or 60 mins), it will only burn a tiny fraction of AP before it gets pushed back to the bottom of the queue.

**The Fix:**
You don't need to disable `OpsiExplore` (as it correctly sleeps for 30 days after the map is clear). Instead, to ensure your AP burns down to your 1200 limit:
1. Ensure your `SuccessInterval` for `OpsiMeowfficerFarming` is lowered (e.g., `5` minutes). 
2. Ensure you leave enough "idle" time where higher-priority tasks (like Events or Main Campaign) are capped or paused, so the bot actually reaches the bottom of its queue to trigger the AP burn.

## 3. Exercise (PvP) Strategy
*   **Current State:** Opponent Choose Mode is `leftmost`, Strategy is `fri18` (which handles reset/quit to prevent losses).
*   **Optimization:** You are correctly prioritizing the leftmost opponent. Since Azur Lane allows you to reset a PvP match before losing (which ALAS handles), fighting the highest-ranked opponent is the best way to maximize Merit and Leaderboard Rank with zero risk. No changes needed here.

## 4. Commission Priorities (Overnight Management)
*   **The Issue:** ALAS struggles to prioritize long (8-hour) or long Urgent commissions specifically at night when the computer is turned off.
*   **Why this happens:** ALAS is designed to run 24/7 and optimize for hourly yields. Its default logic doesn't inherently understand "bedtime." 
*   **Actionable Change:** You need to modify the Custom Filter string to force 8-hour or long urgent commissions to the top of the priority list, or use ALAS's built-in "Major Commission" toggle (if available in your version) to prioritize them before the bot goes offline.

## 5. Main Campaign Farming & Idle Time
*   **The Issue:** The bot sits idle for long stretches of time and could be using that time to farm.
*   **Why this happens:** ALAS's `WhenTaskQueueEmpty` is currently set to `goto_main`, meaning it will sit on the home screen when all scheduled tasks are on cooldown. 
*   **Actionable Change:** Enable a continuous farming task (like Main Campaign or an Event map). As long as the `SuccessInterval` for the farming task is `0` and the `OilLimit` has not been reached, ALAS will default to farming whenever its high-priority daily/hourly tasks are completed. For endgame, setting this to **12-4** (for flexible EXP leveling) or **13-4** (for pure Coin farming) ensures the bot is always productive.

## 6. Administrative Privileges (MEmu Emulator) & Windows Task Scheduler
*   **The Issue:** MEmu requires Administrator privileges to start/stop via CLI, preventing ALAS from managing its lifecycle directly without manual intervention.
*   **The Solution:** Use the Windows Task Scheduler UAC bypass trick.
    *   **How it works:** Create a scheduled task pointing to the emulator or Python script, check "Run with highest privileges", and trigger it via command line (`schtasks /run /tn "ALAS_Start"`).
    *   **Windows 11 Pain Points:**
        1. **Invisible execution:** If you accidentally check "Run whether user is logged on or not", the emulator will launch in "Session 0" (the background). It will run, but you won't be able to see the window. You must use "Run only when user is logged on".
        2. **Working Directory:** Scheduled tasks default their execution path to `C:\Windows\System32`. You *must* fill out the "Start in (optional)" box with your exact ALAS path (`D:\_projects\ALAS_original`), otherwise all relative file paths will break and crash the bot immediately.
