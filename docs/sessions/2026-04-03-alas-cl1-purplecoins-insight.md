# ALAS Anti-Pattern: The CL1 PurpleCoins Hard-Block

> **Purpose of this document:** This note captures a durable behavioral insight extracted from live operation of an external tool (Azur Lane Auto Script, ALAS). It is intended to support the justification for maintaining a local knowledge base of tool behaviors, failure modes, and configuration traps that are not obvious from documentation or UI labels alone.

---

## What We Learned

- `OpsiHazard1Leveling` (CL1 Leveling) is a task that sends fleets to Zone 22 repeatedly to gain EXP.
- When this task is *enabled* in the scheduler, `is_cl1_enabled` becomes `True` **globally** — not just when CL1 is actively running.
- That global flag triggers `check_cl1_purple_coins()` in `module/os_shop/selector.py`, which **unconditionally removes PurpleCoins from the purchase list in both Akashi mystery shops and OS port shops**.
- It also raises the yellow-coin reserve from 35k to 100k.

## Why This Is an Anti-Pattern Even If You Want to Level Characters

1. **It conflates a scheduler flag with a runtime economic state.**  
   The PurpleCoins block applies during *any* OpSi task (`OpsiExplore`, `OpsiDaily`, etc.), not just during CL1. You can be doing completely unrelated tasks and still lose PurpleCoins because a background task happens to be enabled.

2. **It uses an unconditional hard-block where a smarter threshold check already exists.**  
   `get_currency_coins()` in `module/os_shop/shop.py` already subtracts the 100k preserve before deciding how many items to buy. The hard-block in `selector.py` is redundant and overrides that smarter logic, causing missed purchases even when you are far above the safety threshold.

3. **It optimizes a sub-loop at the expense of the primary reward loop.**  
   PurpleCoins are the currency for the actual OpSi endgame rewards (gear design plans, META books, plates). Blocking them to "save yellow coins for Action Points" is backwards: Action Points are a means to an end; PurpleCoins are the end.

4. **It assumes yellow coins are the binding constraint on Action Points.**  
   In practice, Action Points are constrained by shop spawn rates and daily limits, not by yellow coin availability. For any established player, yellow coins accumulate faster than they can be spent on AP. Hoarding them at 100k while blocking PurpleCoins creates a useless surplus of the cheap resource and a deficit of the scarce, valuable one.

5. **It silently overrides user filter strings without warning.**  
   A user may explicitly configure `AkashiShopFilter = "ActionPoint > PurpleCoins"`, but the CL1 block silently discards the `PurpleCoins` part. The UI gives no indication that the user's priority list is being ignored.

## The Fix

**Disable `OpsiHazard1Leveling` entirely.**

This removes the global flag, restores normal shop behavior, and drops the yellow-coin reserve back to 35k. If you actually want the Zone 22 loop, the code should be patched so `check_cl1_purple_coins` respects the existing `yellow_coins_preserve` threshold rather than using an unconditional ban.

## Evidence from Log and Screenshot

- **Log (`2026-04-03_alas.txt`, 10:10:37):** Bot read `SHOP_YELLOW_COINS = 143946` and still logged `Shop buy finished` with PurpleCoins left in the shop.
- **Screenshot (`screenshots/runtime/1775229037754.png`):** Visual confirmation of the Akashi shop with both Action Points marked "Sold out" while the `Special Item` (PurpleCoins, 5x for 400 yellow coins) remained unsold.

## Affected Files in ALAS

- `module/os_shop/selector.py` — `check_cl1_purple_coins` (line ~75)
- `module/os_shop/shop.py` — `yellow_coins_preserve`, `get_currency_coins`
- `module/os_handler/os_status.py` — `is_cl1_enabled`
- `module/os/tasks/hazard_leveling.py` — Zone 22 loop and AP preserve logic
