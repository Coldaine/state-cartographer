# ALAS Interaction Logs

*This log captures insights, configurations, and operations performed in the original ALAS codebase.*

## Date: 2026-04-27

### Activity: Overlapping Event Configuration (April 2026)
**"Here's something we're doing in original ALAS."**

We investigated the codebase to configure ALAS for running two overlapping events simultaneously:
1.  **Event 1 (New Collab):** `event_20260417_cn`
    *   **Structure:** `SP1`, `SP2`, `SP3`, `SP4`, and a daily `SP`.
    *   **Goal:** Farm 70,000 points.
2.  **Event 2 (Lite Rerun):** `event_20260326_cn`
    *   **Structure:** `T1`-`T3`, `HT1`-`HT3`, and a daily `SP`.
    *   **Goal:** Farm high volume (unspecified max).

### Configuration Strategy Discovered:
Because ALAS tasks operate independently, we can wire them to different events to accomplish complex daily goals:

1.  **Handling Daily Multipliers (First-Clears):**
    *   Use the **`EventDaily`** task (often labeled EventA/B/C).
    *   Set `Campaign.Event` to the specific folder (e.g., `event_20260417_cn`).
    *   Set the `StageFilter` to define the clear sequence (e.g., `SP1 > SP2 > SP3 > SP4`).

2.  **Handling the Standalone Daily SP Stage:**
    *   Use the dedicated **`EventSp`** task.
    *   Set `Campaign.Name` to `sp`.
    *   Set `Campaign.Event` to whichever event's SP stage is currently being missed (e.g., `event_20260326_cn`).

3.  **Handling the Main Point Grinds:**
    *   **For the 70k point goal:** Use the **`Event`** task. Point it to `event_20260417_cn`, stage `SP4`. In the `EventGeneral` settings, set `PtLimit` to `70000`.
    *   **For the high-volume rerun grind:** Use the **`Event2`** task. Point it to `event_20260326_cn`, stage `HT3`. Let it run on the standard oil limit constraints.