# Runtime Architecture: VLM-First Navigation

How State Cartographer uses the ALAS navigation graph with VLM-based observation.

## The Runtime Loop

```text
OBSERVE → ROUTE → EXECUTE → repeat
```

1. **OBSERVE**: Take a screenshot. Send it to the VLM (OpenAI-compatible endpoint). Ask: "What buttons are on this screen and where are they?" The VLM returns a button inventory — labels and positions. The button inventory IS the current state. No separate page classification step.

2. **ROUTE**: Given the current state (button inventory) and a target page, query the navigation graph (BFS) to get a sequence of symbolic button names to tap. Example: to reach page_commission from page_main, the route is `[MAIN_GOTO_REWARD, REWARD_GOTO_COMMISSION]`.

3. **EXECUTE**: The VLM already told you where each button is. Tap the next button in the route sequence. Wait for the transition (~1-2s). Return to OBSERVE to verify you arrived.

If a popup appears (unexpected buttons/dialog), the VLM sees it and the runtime either dismisses it (if it's a dismiss-only popup) or makes a task-context-dependent decision. If the VLM sees something completely novel, it can reason about it or escalate.

## What Comes From Where


| Component | Source | Notes |
|-----------|--------|-------|
| **Navigation graph** | Extracted from ALAS `page.py` | 43 pages, 107 edges, symbolic button names. Used for routing (BFS). See [ALS-navigation-graph.md](ALS-navigation-graph.md) |
| **Observation** | VLM via OpenAI-compatible endpoint | Returns button inventory = state + available actions. No template matching. |
| **Button positions** | VLM observation at runtime | Not hardcoded. The VLM sees where buttons are on the current screenshot. |
| **Popup handling** | VLM observation + task context | Known popups cataloged in [ALS-navigation-graph.md](ALS-navigation-graph.md). Novel popups handled by VLM reasoning. |
| **Transport** | `state_cartographer/transport/` | ADB screencap (Vulkan, 100% reliable), MaaTouch tap. Done. |


## Key Design Decisions

**VLM-first (Phase 1).** The VLM is the only observation method. No template matching, no embedding classifiers. Start simple, prove it works. Optimization (CLIP embeddings, caching) is Phase 2 — deferred until Phase 1 is working end-to-end. See issue #34.

**OpenAI-compatible endpoint.** The VLM endpoint must use the OpenAI chat completions API with image input. This ensures provider flexibility — local models (llama-swap, ollama, vllm) or free remote providers. See `docs/decisions.md` (2026-04-03 entry).

**Button inventory = state.** There is no separate "classify which page I'm on" step. The set of visible buttons defines the state. If you see Campaign, Fleet, Dock, Reward — you're on main. The VLM returns both identity and available actions in one call.

**Symbolic routing, VLM-resolved coordinates.** The navigation graph uses symbolic button names (BACK, HOME, MAIN_GOTO_CAMPAIGN). The VLM resolves these to screen coordinates at observation time. No hardcoded pixel positions in the graph.

**Event pages always use VLM.** Events change every 2-4 weeks with completely different UI. No cached or pre-computed approach survives event rotations. The VLM handles them the same way it handles any other screen — observe buttons, report positions.

**Popups are ephemeral states.** They overlay the page graph. Some are dismiss-only (tap and return to previous page). Some are decision states requiring task context. Novel popups the system has never seen are handled by VLM reasoning — this is the advantage over ALAS's hardcoded popup handlers.

## Progressive Determinism

As the VLM consistently observes the same button at the same position across many screenshots, the system can cache that as a learned observation. Subsequent navigation can skip the VLM call for that step (Tier 0). This is earned from observation, not hardcoded from ALAS.

The ALAS graph serves as a **test oracle**: compare VLM observations against the known graph to measure quality. "The VLM says HOME is at top-right. ALAS agrees. Confidence earned."

## What This Is Not

- This is not wrapping ALAS. The VLM observes independently.
- The ALAS graph is routing topology and test oracle, not VLM vocabulary.
- The popup catalog is reference material, not a rulebook. The VLM handles novel popups ALAS never saw.
- Pixel coordinates in the navigation graph doc are ALAS reference data at 1280x720. The runtime does not use them — the VLM resolves positions from the live screenshot.
