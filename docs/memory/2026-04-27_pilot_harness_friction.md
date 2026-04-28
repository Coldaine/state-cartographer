# Retrospective: Agentic Piloting Friction (2026-04-27)

*This document captures the difficulties encountered when using subagents to pilot the MasterStateMachine harness to map concurrent Azur Lane events.*

## 1. Simulated Date & Search Hallucination
*   **Difficulty:** The session was grounded in a future date (**April 2026**). 
*   **Impact:** Main-agent web searches returned hallucinated event data (e.g., mixing real historical DOA collab data with fictional 2026 lore). This initially led to incorrect subagent briefings.
*   **Lesson:** Ground truth must be pulled from **local codebase files** (`campaign/*.py`) first. Web search is a secondary fallback, not a primary source for future-dated sessions.

## 2. Turn-Limit Interruption for Multi-Step Loops
*   **Difficulty:** Navigating from Home -> Battle -> Event Selection -> Event Map -> Analyze -> Home is a multi-step sequence.
*   **Impact:** Subagents repeatedly hit internal turn limits before completing the cycle. This caused "fragmented mapping" where Event A was verified but Event B was missed.
*   **Lesson:** Complex piloting should be "check-pointed." Subagents need to explicitly log state to disk so a follow-up agent can resume immediately without re-resetting.

## 3. Normalized vs. Physical Coordinate Mapping
*   **Difficulty:** VLMs (like Flash) return coordinates in a normalized `0-1000` system. The physical emulator uses pixels (e.g., `1280x720`).
*   **Impact:** Subagents "flailed" on the logic of translating these coordinates for `pilot.tap(x, y)`.
*   **Lesson:** The `Pilot` facade should ideally handle coordinate normalization internally, or a standard helper script should be provided to subagents to perform this scaling deterministically.

## 4. Requirement for Procedural "Code-First" Briefings
*   **Difficulty:** Vague goals (e.g., "Go find the SP stage") led to subagent flailing.
*   **Impact:** The agent would stare at the screen or navigate to the wrong tabs because it didn't know the game's UX patterns.
*   **Lesson:** Subagents require a **procedural script skeleton** in their prompt. Instead of "Map the event," the prompt must be: "1. Reset home. 2. Tap Banner X. 3. Screen 1. 4. Analyze Nodes."

## 5. Visual Ambiguity in Map Tab Navigation
*   **Difficulty:** Identifying map sub-tabs (Normal vs. Hard vs. EX) proved difficult for the VLM without specific context.
*   **Impact:** The agent would land on the EX tab by default (game behavior) and try to find T3 stages there, failing because EX only contains "EXTRA" nodes.
*   **Lesson:** Explicitly instruct agents to verify the **Tab State** before mapping stages. Use standard labels like `["normal_tab", "hard_tab", "ex_tab"]` in `detect_page`.
