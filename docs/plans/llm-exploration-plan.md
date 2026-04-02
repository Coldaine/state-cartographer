# LLM Exploration Plan — Daily Task Piloting

Status: active
Date: 2026-03-31

## Goal

I (the LLM) manually pilot through Azur Lane's daily tasks using the Pilot transport layer and my own vision. As I go, I document every screen, every transition, every failure. This produces the state machine data that no amount of offline labeling can match — because I'm actually driving.

## Method

1. Take a screenshot
2. Look at it (vision) — identify what page I'm on
3. Decide what to do (tap, press, swipe)
4. Execute via Pilot
5. Take another screenshot — verify the transition
6. Log: page_before → action → page_after
7. If stuck, try recovery (BACK, HOME, press)
8. Periodically: hand observations to a subagent for state machine synthesis

## What I'm Building As I Go

- **Transition log**: (source_page, action, target_page) triples
- **Page catalog**: what each screen looks like, key visual features
- **Problem spots**: where taps fail, where navigation breaks, where popups block
- **Timing data**: how long each transition takes

## Daily Task Order (from ALAS)

Starting simple, building up:

### Phase 1 — Orient & Navigate (do first)
1. Identify current screen (wherever the game is)
2. Navigate to main/home screen
3. Navigate to Reward page and back
4. Navigate to Campaign menu and back
5. Prove I can get between the 3 major hubs

### Phase 2 — Reward Collection (simplest tasks)
6. Collect passive rewards (oil, coins, exp) from main screen
7. Check mission rewards (page_mission)
8. Check mail (page_mail)

### Phase 3 — Commission Management
9. Navigate to commission list
10. Read commission status (which are running, which are done)
11. Collect completed commission rewards
12. Start new commissions if slots available

### Phase 4 — Dorm / Research / Meowfficer
13. Visit dorm — feed if needed
14. Visit research — collect/start
15. Visit meowfficer — collect if available

### Phase 5 — Daily Missions & Exercise
16. Enter daily missions (page_daily)
17. Attempt a daily battle
18. Visit exercise (PvP)

### Phase 6 — Campaign / Combat
19. Enter main campaign
20. Attempt a sortie (actual combat loop)

## Driving Interface

```python
# Each action I take follows this pattern:
from state_cartographer.transport import Pilot
pilot = Pilot()
pilot.connect()

# 1. See
png = pilot.screenshot()
# (I view the image and decide)

# 2. Act
pilot.tap(x, y)       # coordinate tap
pilot.press("primary") # semantic key (Space=confirm, Tab=back, etc.)
pilot.swipe(x1, y1, x2, y2)  # scroll/pan

# 3. Verify
png2 = pilot.screenshot()
# (I view and confirm transition)
```

## KEYMAP Reference (MEmu bindings)

| Name | Keycode | Game Region |
|------|---------|-------------|
| primary | 62 (Space) | Main action / Confirm |
| back | 61 (Tab) | Back / Cancel |
| confirm | 66 (Enter) | Secondary confirm |
| cancel | 111 (Escape) | System menu |
| fleet1 | 8 (1) | Fleet 1 select |
| fleet2 | 9 (2) | Fleet 2 select |
| engage | 45 (Q) | Engage nearest |
| objective | 33 (E) | Next objective |
| up | 51 (W) | Pan up |
| left | 29 (A) | Pan left |
| down | 47 (S) | Pan down |
| right | 32 (D) | Pan right |
| emergency | 120 (F9) | Kill app |

## Output Artifacts

As I drive, I append observations to a dated session log under `docs/sessions/`.
Periodically, a subagent synthesizes the accumulated transitions into structured data.
