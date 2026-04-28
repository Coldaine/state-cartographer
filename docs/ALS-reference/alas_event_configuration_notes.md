# ALAS Event Configuration Notes

*This document captures configuration patterns and logic extracted from the original Azur Lane Auto Script (ALAS) repository, specifically regarding overlapping event handling and point farming.*

## Context
In late April 2026, two events were running concurrently:
1. **"Vacation Lane - Beachside Brilliance" (New DOA Collab):** Internal folder `event_20260417_cn`. Stage structure: `SP1` to `SP4`, plus a daily `SP`.
2. **"Vacation Lane (Lite Rerun)" (or overlapping event):** Internal folder `event_20260326_cn`. Stage structure: Normal `T1`-`T3`, Hard `HT1`-`HT3`, plus a daily `SP`.

## ALAS Task Wiring for Dual Events

ALAS uses separate scheduler tasks to handle different event farming goals simultaneously. The following mapping illustrates how to wire the tasks to achieve specific goals:

### 1. Daily Multipliers (First-Clear Bonuses)
**Goal:** Run specific stages once daily to consume point multipliers.
**Task:** `EventDaily` (labeled as `EventA`, `EventB`, etc. in GUI).
**Configuration:**
*   **Campaign Event:** Set to the internal folder name (e.g., `event_20260417_cn` or `event_20260326_cn`).
*   **StageFilter:** Define the sequence. 
    *   *DOA Collab example:* `SP1 > SP2 > SP3 > SP4`
    *   *Rerun example:* `T1 > T2 > T3` or `HT1 > HT2 > HT3`

### 2. Daily Special Stage (SP)
**Goal:** Clear the standalone daily `SP` stage (no number suffix) that gives a high point yield.
**Task:** `EventSp`
**Configuration:**
*   **Campaign Name:** `sp`
*   **Campaign Event:** Set strictly to the folder name of the event missing the clear (e.g., `event_20260326_cn`).

### 3. High-Volume Point Farming (Final Stages)
**Goal:** Continuously farm the final stages of events (e.g., to hit point milestones or burn oil).
**Tasks:** `Event` (Primary) and `Event2` (Secondary)

**Primary Event Farming (e.g., 70,000 Point Goal):**
*   **Task:** `Event`
*   **Campaign Name:** `SP4`
*   **Campaign Event:** `event_20260417_cn`
*   **EventGeneral -> PtLimit:** `70000` (Stops execution when this point threshold is reached).

**Secondary Event Farming (e.g., Rerun Stockpile):**
*   **Task:** `Event2`
*   **Campaign Name:** `HT3`
*   **Campaign Event:** `event_20260326_cn`
*   **Stop Condition:** Set to run indefinitely or tie to an oil limit.