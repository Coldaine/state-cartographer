# Technical Hypothesis: The "Stability Trap" (UI Paralysis)

> Historical note: moved from `docs/research/RES-stability-trap-analysis.md` during the 2026 documentation realignment.


## 1. Problem Statement
The bot frequently enters a state where it "does nothing" for several minutes, eventually triggering a `GameStuckError` and a full app restart. This occurs even when the game is clearly on the correct screen and the bot is successfully capturing at least some valid (non-black) frames.

## 2. Theoretical Basis: The ALAS Stability Timer
ALAS (AzurLaneAutoScript) uses a `Timer(count=N)` class to handle UI transitions. 

### The Algorithm:
1. The bot searches for a specific UI element (e.g., `MAIN_GOTO_CAMPAIGN`).
2. If it finds the element, it increments a **consecutive success counter**.
3. If it **fails** to find the element (or sees a black frame), the counter is **immediately reset to 0**.
4. The bot will **only** take an action (click or transition) when the counter reaches `N` (usually `count=3` or `count=5`).

### The Mathematical Conflict:
On the current Win32 MEmu + DirectX harness, the screenshot pipeline (DroidCast/ADB) is producing valid frames at a low success rate (~10-20%), with "Black Frames" filling the gaps.

* **Probability of 1 valid frame:** $P \approx 0.2$
* **Probability of 3 consecutive valid frames:** $P^3 \approx (0.2)^3 = 0.008$ (less than 1%)

**Result:** The bot is "blinking" so frequently that it can almost never achieve a streak of 3 valid frames. Even if it sees the correct button at $T=0$, a black frame at $T+1$ wipes its "memory," causing it to wait indefinitely for a stability streak that is statistically impossible.

## 3. Empirical Evidence (From `data/raw_stream`)
Looking at the harvest from **2026-03-20 02:20**:

| Timestamp | Frame Hash/Size | Status | Bot Memory (Counter) |
|-----------|-----------------|--------|----------------------|
| 02:20:40 | 2.7 KB | **BLACK** | 0 |
| 02:20:41 | 1.1 MB | **VALID** | 1 |
| 02:20:42 | 2.7 KB | **BLACK** | **RESET TO 0** |
| 02:20:43 | 2.7 KB | **BLACK** | 0 |
| 02:20:44 | 2.7 KB | **BLACK** | 0 |
| 02:20:45 | 65.5 KB | **PARTIAL** | 0 |

**Conclusion:** The bot saw a perfect frame at `02:20:41`, but it could not act on it because the very next frame was black. To the bot's logic, the UI "disappeared," so it aborted the click and stayed "idle."

## 4. Proposed Mitigation
We have begun relaxing the `count` requirement in high-traffic modules:
* `module/research/research.py`: `count=3 -> count=1`
* `module/guild/lobby.py`: `count=3 -> count=1`
* `module/freebies/supply_pack.py`: `count=3 -> count=1`

**Goal:** Allow the bot to "punch through" on a single valid frame without requiring a streak.

## 5. Alternative Explanations (Not yet ruled out)
* **MaaTouch vs. ADB Control:** It's possible the click commands are being sent but the emulator isn't processing them due to the same rendering hang that causes black frames.
* **UI Overlays:** Transparent "Loading" or "Connecting" spinners might be present but invisible to the bot's current assets, causing it to wait for a "clear" screen that never comes.
