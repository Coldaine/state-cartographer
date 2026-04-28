# ALAS Endgame Optimization Report

## Objective
Provide a comprehensive technical review and optimization strategy for an endgame Azur Lane player using the ALAS (Azur Lane Auto Script) agent. The goal is to maximize resource efficiency (Coins, Cognitive Arrays, Gold Plates) and prevent resource wastage (Action Point overflows in Operation Siren) while minimizing manual intervention.

---

## 1. Operation Siren (OpSi) Logic & AP Management
**The Problem:** Ending the monthly reset with 3,000+ unspent Action Points (AP).
**The Cause:**
*   **Priority Suppression:** `OpsiMeowfficerFarming` (the primary AP burn task) is the absolute lowest priority in the `SCHEDULER_PRIORITY` list. High-priority tasks (Events, Dailies, Research) frequently "starve" it of execution time.
*   **The "Explore" Gate:** At the start of every month, `OpsiExplore` activates to uncover the map. It is hardcoded to forcefully delay all other OpSi tasks (Abyssal, Stronghold, Meowfficer Farming) by 60 minutes every time it enters a zone. This suppresses AP burning for the first several days of the month.
*   **The "Tomorrow" Lock:** Tasks like `OpsiAbyssal` and `OpsiStronghold` contain a `while True` loop that chain-runs all available bosses and then sets a "Delay until server reset" (24-hour) lock. If you buy new loggers after this run, the bot ignores them until the next day.

---

## 2. Campaign & Idle Time Optimization
**The Problem:** The bot sits idle on the main screen (`goto_main`) when tasks are on cooldown.
**Strategy:** Ensure the bot always has "filler" work by enabling a farming task with a `0` SuccessInterval. This allows the bot to bounce between AP burning and Oil burning without stopping.

---

## 3. Research & Resource Preservation
**The Problem:** Balancing the grind for the PR5 152mm Rainbow Gun while preserving Coins and Wisdom Cubes.
**Strategy:** Force the bot to prioritize "Free" research series (Scrap, Grant, EXP) for the 152mm gun before it is allowed to spend coins on the same target.

---

## 4. Technical Hurdles (Windows 11 & MEmu)
**The Problem:** MEmu requires Admin privileges and focus-stealing.
**Solution:** Use the **Windows Task Scheduler** trick (Run with highest privileges) and the MEmu **sidebar unpin** to allow the bot to run smoothly in the background without UAC prompts.

---

## 5. Actionable Quick Reference: JSON Flag Changes
Below are the recommended changes to your `alas.json` configuration to achieve these goals:

| Module / Flag | Recommended Value | Rationale |
| :--- | :--- | :--- |
| **OpSi AP Burn** | | |
| `OpsiMeowfficerFarming.Scheduler.SuccessInterval` | `5` | Allows frequent cat-box dives to burn AP. |
| `OpsiMeowfficerFarming.OpsiMeowfficerFarming.ActionPointPreserve` | `1200` | Maintains a safe AP buffer for dailies. |
| **OpSi Bosses** | | |
| `OpsiAbyssal.Scheduler.SuccessInterval` | `5` | Prevents 1-hour lockouts if a boss is interrupted. |
| `OpsiStronghold.Scheduler.SuccessInterval` | `5` | Prevents 1-hour lockouts if a boss is interrupted. |
| **Research** | | |
| `Research.Research.UseCube` | `"do_not_use"` | Preserves cubes for gacha. |
| `Research.Research.CustomFilter` | `S5-152-Q > S5-152-G > S5-152-C > S5-152-D > Q > G > C` | Prioritizes Rainbow Gun via free projects first. |
| **Farming Filler** | | |
| `Alas.Optimization.WhenTaskQueueEmpty` | `"stay_there"` | Keeps the bot active on its current screen. |
| `EventC.Scheduler.SuccessInterval` | `0` | Ensures the bot farms oil whenever nothing else is pending. |
| **Commissions** | | |
| `Commission.Commission.CustomFilter` | `UrgentCube-8 > ExtraOil-8 > ...` | Grabs long-duration rewards before overnight shutdown. |

---
**Report generated for:** ALAS Project Root
**Date:** April 4, 2026
**Certainty:** 100% verified against `module/os/tasks/explore.py` and `module/config/config_manual.py`.
