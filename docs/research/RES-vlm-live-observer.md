# RES — VLM as Continuous Live Observer

**Status: Design (March 2026)**

This document captures the capability space that opens up when the VLM tier
is treated as a *continuous live observer* rather than a batch analysis tool.
It is the architectural complement to `RES-vlm-replay-analysis.md`, which
covers the research foundations for replay/corpus patterns. This doc covers
what those patterns enable in a *running session*.

---

## The framing shift

In the current design, VLM is used in two ways:

1. **Bootstrap classifier** – temporary, to be replaced by pixel anchors once
   enough labeled corpus exists
2. **Retrospective analysis** – replay a clip after a failure, label corpus
   frames, extract graph triples from a session recording

Both are offline or on-demand. Neither treats the VLM as a persistent witness
to the live session.

The framing shift: **the small VLM runs continuously, emitting a state stream.
Claude reads the stream like a log and escalates into images only when needed.**

This is not the same as "VLM checks each frame." It is a compression model:
the VLM reduces N frames/second to a sparse, human-readable event stream, and
the supervisor (Claude) operates on that stream without looking at raw pixels
unless something breaks.

---

## The state stream

The always-on small VLM (target: Qwen 0.8B or equivalent, <1s latency) emits
a NDJSON stream to `data/state_stream/` or pipes directly to the runtime:

```json
{"ts": "20260320_134204_477", "page": "page_commission", "conf": 0.97, "note": null}
{"ts": "20260320_134210_123", "page": "page_commission", "conf": 0.91, "note": "collect_all_visible"}
{"ts": "20260320_134215_882", "page": "page_main", "conf": 0.99, "note": null}
{"ts": "20260320_134301_044", "page": "unknown", "conf": 0.31, "note": "popup_unrecognized"}
```

Key fields:
- `ts` — millisecond timestamp, matches the raw_stream filename
- `page` — state ID from graph.json, or `"unknown"`
- `conf` — confidence (0–1). Below ~0.6 = escalate
- `note` — optional free-text from VLM about *what it sees beyond the page ID*.
  Examples: `"collect_all_visible"`, `"dorm_bar_low"`, `"event_banner_present"`,
  `"popup_unrecognized"`, `"login_spinner"`

The `note` field is the key to the richer capabilities below. It is optional
and sparse — only emitted when the VLM observes something worth flagging. This
keeps the stream cheap while preserving signal.

---

## What this stream enables

### 1. Claude as a log reader, not a screenshot consumer

The supervisor workflow changes fundamentally:

**Current (implicit) model:**
- Claude receives a screenshot
- Claude classifies the state
- Claude decides what to do
- Claude calls a tool

**Stream model:**
- Runtime plays the loop autonomously
- State stream flows continuously
- Claude reads the stream summary on request or when escalated
- Claude looks at a screenshot only when: conf drops, `unknown` appears, anomaly
  is flagged, or supervisor explicitly queries

This is the Mobile-Agent-v2 compression pattern from `RES-vlm-replay-analysis.md`
applied to a live session: one image + text summary of recent history = full
context without scanning N frames.

---

### 2. Session memory from visual evidence

Because the stream is timestamped and persistent, the runtime can answer
retrospective questions without replaying raw frames:

```
Q: "How many times have we been in page_dorm this session?"
A: grep the stream for page_dorm — 4 entries, at 13:12, 13:45, 14:18, 14:51

Q: "When did we last collect commissions?"
A: last page_commission entry at 13:42 (94 minutes ago)

Q: "Has the dorm_bar_low note appeared today?"
A: yes, twice — at 13:44 and 14:50
```

None of this requires looking at a screenshot. The stream is the memory.

---

### 3. Anomaly detection

The VLM emits `"unknown"` or a low-confidence note when it sees something
outside its training distribution. The runtime can flag these automatically:

- **New popup** not in corpus → `conf < 0.4`, `note: "popup_unrecognized"` →
  runtime pauses, saves frame, escalates with note
- **New event banner** → `note: "event_banner_present"` → runtime can check
  whether this is a known event type, escalate if not
- **Game update** changed a UI element → pixel anchors fire but conf drops on
  small VLM → mismatch triggers recalibration alert

The rule is simple: anything below a confidence threshold, or any `note` that
doesn't match a known pattern, becomes an escalation candidate.

---

### 4. Rich escalation payloads

When the runtime escalates to Claude, it sends not just a screenshot but a
**temporal payload**:

```json
{
  "escalation_reason": "page_unknown for 47 seconds",
  "current_frame": "<path to PNG>",
  "recent_stream": [
    {"ts": "...", "page": "page_dorm", "conf": 0.99},
    {"ts": "...", "page": "page_dorm", "conf": 0.94, "note": "popup_unrecognized"},
    {"ts": "...", "page": "unknown", "conf": 0.28},
    ...
  ],
  "vlm_candidates": ["page_dorm_popup_daily", "page_event_banner", "page_unknown"],
  "pixel_anchor_result": "page_dorm",
  "conflict": "pixel_anchor says page_dorm, vlm says unknown",
  "last_alas_action": "tap(782, 441)",
  "suggested_recovery": "tap dismiss region or GOTO_MAIN"
}
```

This is NORTH_STAR goal #11 ("escalation is rich, not blind") made concrete.
The supervisor gets enough context to decide without re-investigating.

---

### 5. The VLM as a session historian

After a run, Claude can ask:

> "Summarize what happened in this session."

The runtime constructs a narrative from the stream without requiring Claude to
review 1200 raw frames:

```
Session: 2026-03-20 13:12 – 14:58 (106 minutes)
Pages visited: page_main (22x), page_commission (4x), page_dorm (4x),
               page_research (2x), page_exercise (1x), page_opsimain (3x)
Notable events:
  - 13:44: dorm_bar_low noted, refilled at 13:45
  - 14:03: popup_unrecognized appeared on page_dorm (frame saved)
  - 14:31: page_unknown for 47 seconds → GOTO_MAIN recovery used
  - 14:58: session ended normally
Tasks completed per ALAS log: Commission (x4), Dorm (x3), Research (x1)
```

This is the compressed-history model in its most useful form. The VLM watched
everything; Claude reads a paragraph.

---

### 6. Temporal pattern recognition across sessions

Across multiple sessions, the stream accumulates evidence:

- "The bot gets stuck on page_dorm's popup in 3 of 4 recent sessions" →
  this is a systematic issue, not a one-off
- "page_unknown appears consistently around 14:30" → probably a scheduled
  in-game event that triggers a new popup
- "conf on page_exercise is dropping over time" → game update probably changed
  the page's visual design, anchors need recalibration

This requires nothing but streaming the NDJSON files across sessions and
grouping by pattern.

---

### 7. Real-time game event detection

The game regularly introduces new content: limited events, seasonal campaigns,
maintenance notices. The VLM is the first line of detection because it sees
the actual pixels, not just the state graph.

A `note` field that reads `"seasonal_event_banner"` or `"maintenance_warning"`
is high-value signal that a purely deterministic system cannot produce. The
VLM doesn't need to classify these perfectly — it just needs to flag "something
new is on screen" so the supervisor can investigate.

---

## Operational model

```
Small VLM (always-on, <1s)
    → state stream: {ts, page, conf, note}
    → stored in data/state_stream/YYYY-MM-DD.ndjson

Runtime reads stream:
    → if conf >= threshold and no anomaly notes: continue autonomously
    → if conf < threshold or unknown: pause and escalate
    → if note matches known pattern (e.g. dorm_bar_low): handle automatically

On escalation:
    → assemble temporal payload (recent stream + current frame + conflict info)
    → push to supervisor (Claude via MCP or websocket)

Claude operates on:
    → text stream summary (fast, cheap)
    → single current frame (only when needed)
    → never scans N raw frames unless explicitly debugging
```

---

## What needs to be built

| Component | Status | Needed for |
|-----------|--------|-----------|
| Small VLM server (Qwen 0.8B) | Planned | Always-on classifier |
| State stream emitter | Not started | All of the above |
| Stream reader / query interface | Not started | Session memory, history |
| Anomaly detection rules | Not started | Escalation, event detection |
| Escalation payload builder | Not started | Rich supervisor context |
| Session summarizer | Not started | VLM as historian |
| Cross-session pattern aggregator | Not started | Temporal pattern recognition |

The large VLM (Qwen3.5-9B-AWQ @ localhost:18900) is **already running** and
handles the `note` generation / anomaly description task today, just not in a
continuous streaming mode. The missing piece is the emission loop and the
stream consumer.

---

## Relationship to existing docs

| Doc | Relationship |
|-----|-------------|
| `RES-vlm-replay-analysis.md` | Research foundations — 6 patterns, all retrospective |
| `OBS-overview.md` | Vision tier table — names the small VLM but not what it enables |
| `docs/NORTH_STAR.md` | Goals #10 and #11 assume this exists (rich escalation) |
| `ALS-live-ops.md` | Hard rules for when to escalate (human takeover, duplicates) |
| `AUT-overview.md` | Lists escalation mechanism as missing — this doc addresses it |
