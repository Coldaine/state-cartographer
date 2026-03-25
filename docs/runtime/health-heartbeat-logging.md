# Runtime Health, Heartbeat, and Logging Design

**Status:** Concrete design for the runtime health and event layers.

How the repo classifies health, emits heartbeats, and records local evidence.

The key principle: a missing preferred tool (MaaTouch not deployed) does not mean transport failure. If ADB is reachable and fallback control works, that is DEGRADED, not UNREACHABLE.

## Readiness Tiers

Three exclusive tiers:

| Tier | Meaning | Can run workflow |
|------|---------|-----------------|
| `unreachable` | No device communication. ADB missing, serial unreachable, or device offline after reconnect. | No |
| `degraded` | Transport reachable but posture limited. Examples: MaaTouch not deployed (using ADB input fallback), observation unverified. | Supervised only |
| `operable` | Transport reachable and preferred control posture available. | Supervised only |

### Degradation Codes

Explicit reasons attached to the current report:

- `preferred_input_missing` — MaaTouch not deployed, using ADB shell input fallback
- `debug_only_visual` — scrcpy available but not usable as runtime frame source
- `visual_tool_missing` — no visual debug tool attached
- `frame_freshness_unproven` — have not yet verified frame timestamps
- `action_ack_weak` — action dispatch works but semantic verification not yet proven
- `workflow_progress_unproven` — no workflow-level progress proof yet
- `high_latency` — capture or action latency exceeds thresholds
- `intermittent_disconnects` — ADB session drops seen

### Example truthful report

`
tier = degraded
degradation_codes = [preferred_input_missing, frame_freshness_unproven]
`

## Layer Status Model

Report independently:

- **transport:** `unreachable` or `ready` — is ADB reachable?
- **control:** `unavailable`, `fallback`, or `preferred` — MaaTouch active, ADB input fallback, or nothing?
- **observation:** `unavailable` or `unverified` — can we capture frames?

## Heartbeat Design

Five layers, each with its own cadence during active execution:

| Layer | Cadence | Checks |
|-------|---------|--------|
| ADB transport | 2s | serial online, shell works |
| Control surface | 5s | MaaTouch or ADB input responds |
| Frame freshness | per capture + 3s watchdog | frame captured, decodable, timestamped |
| Action acknowledgement | per action | pre/post evidence, semantic change |
| Workflow progress | 15s no-progress watchdog | objective advanced or quarantined |

## Escalation Ladder

| Level | Trigger | Allowed actions |
|-------|---------|-----------------|
| 0 Observe | first anomaly | record miss, capture diagnostic frame |
| 1 Retry | transient miss | reissue same command once |
| 2 Re-establish | same layer missed twice | reconnect ADB, redeploy MaaTouch |
| 3 Re-prove | substrate back but unproven | fresh capture + benign action ack |
| 4 Runtime recovery | workflow failed despite healthy substrate | navigate to known-safe page |
| 5 Incident quarantine | repeated Level 4 | incident bundle, stop and escalate |

## Event Schema

Two append-only NDJSON streams:
- `tooling` — what the substrate did
- `runtime` — why we asked and whether the workflow moved

### Envelope

`json
{
  "ts": "2026-03-25T18:41:09.812Z",
  "event_id": "evt-...",
  "stream": "runtime",
  "kind": "action_ack",
  "name": "tap_ack",
  "session_id": "sess-...",
  "serial": "127.0.0.1:21503",
  "component": "runtime.verifier",
  "ok": true,
  "readiness_tier": "degraded",
  "degradation_codes": ["preferred_input_missing"]
}
`

### Required event families

Tooling: `bootstrap`, `health_transition`, `heartbeat`, `frame_capture`, `input_dispatch`, `recovery_step`, `incident`, `session_end`

Runtime: `session_start`, `observation`, `action_ack`, `workflow_progress`, `incident`, `session_end`

## File Layout

`
data/
  events/
    tooling/YYYY-MM-DD/<session_id>/tooling.ndjson
    runtime/YYYY-MM-DD/<session_id>/runtime.ndjson
    incidents/YYYY-MM-DD/<incident_id>/incident.ndjson
  logs/
    tooling/YYYY-MM-DD/<session_id>/transport.log
    runtime/YYYY-MM-DD/<session_id>/runtime.log
  artifacts/
    sessions/YYYY-MM-DD/<session_id>/frames/
    incidents/YYYY-MM-DD/<incident_id>/
`

## Implementation Phases

### Phase 1 — Fix truthfulness at transport layer
- 3-tier readiness + degradation codes in DoctorReport
- Per-layer statuses reported independently
- Structured tooling events under `data/events/tooling/`

### Phase 2 — Runtime heartbeat and action acknowledgement
- Separate runtime event writer from tooling event writer
- Per-action `action_id` and `attempt_id`
- Before/after frame references on meaningful actions
- Workflow no-progress watchdog

### Phase 3 — Incident bundles and production gate
- Incident bundling across both streams
- Promotion gate: stable preferred stack + fresh-frame proof + action ack + watchdog + one forced-failure drill
