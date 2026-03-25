# Runtime Health, Heartbeat, and Logging Design

Status: concrete design proposal for the next runtime slice.

This document defines how the repo should classify health, emit heartbeats, and record local evidence for live emulator control.

The current repo problem is not lack of probes; it is lack of **correct separation between layers**. A missing preferred tool must not be reported as a transport failure when ADB reachability and fallback control are still healthy.

See also:
- [runtime-overview.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/runtime-overview.md)
- [agent-control-tool-requirements.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/agent-control-tool-requirements.md)
- [borrowed-control-tool-setup.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/borrowed-control-tool-setup.md)
- [2026-03-25-memu-transport-probe-results.md](/mnt/d/_projects/MasterStateMachine/docs/memory/2026-03-25-memu-transport-probe-results.md)

## Design Stance

Health must be modeled as:
- one **readiness tier**
- one set of **layer statuses**
- zero or more **degradation codes**
- one **evidence bundle**

## Readiness Tiers

Use three exclusive tiers:

| Tier | Meaning | Can run workflow |
|------|---------|-----------------|
| `unreachable` | No pinned-device communication. `adb` missing, serial unreachable, or device offline after reconnect. | No |
| `degraded` | Transport is reachable, but the current posture is limited or fallback-backed. Examples: preferred Maa stack missing, observation still unverified, visual path debug-only. | Supervised only |
| `operable` | Transport is reachable and the preferred control posture is available for the current machine. | Supervised only |

`reachable` from the old 5-tier model is dropped. The useful distinction is now `unreachable` vs `degraded` vs `operable`.

### Degradation flags

Degradation codes are explicit reasons attached to the current report. A truthful transport-side report on the current pinned machine looks like:

```
tier = degraded
degradation_codes = [observation_unverified, preferred_stack_missing, debug_only_visual]
```

This is much more useful than a sad `fail`.

### Required degradation codes

- `preferred_stack_missing`
- `debug_only_visual`
- `visual_tool_missing`
- `frame_freshness_unproven`
- `action_ack_weak`
- `workflow_progress_unproven`
- `high_latency`
- `intermittent_disconnects`

## Layer Status Model

Transport-facing `DoctorReport` layers should be reported independently:

- transport: `unreachable` or `ready`
- control: `unavailable`, `fallback`, or `preferred`
- observation: `unavailable` or `unverified`

Runtime-level heartbeats may later add richer semantic status on top of those transport-layer values, but the base transport report should not collapse them into a single generic label.

Each layer record also carries:
- `checked_at`
- `evidence_age_ms`
- `reason_codes`
- `last_success_at`
- `last_failure_at`
- `consecutive_failures`

## Heartbeat Design

Five layers, each with its own cadence during active execution:

| Layer | Cadence (active) | Checks |
|-------|-----------------|--------|
| ADB transport | 2s | serial still online, shell works |
| Control surface | 5s | tool responds, session alive |
| Frame freshness | per capture + 3s watchdog | frame captured, decodable, timestamped |
| Action acknowledgement | per action | pre/post evidence, semantic change |
| Workflow progress | 15s no-progress watchdog | objective advanced or quarantined |

## Escalation Ladder

| Level | Trigger | Allowed actions |
|-------|---------|-----------------|
| 0 Observe | first anomaly | record miss, capture diagnostic frame |
| 1 Retry | transient miss | reissue same command once |
| 2 Re-establish layer | same layer missed twice | reconnect ADB, reattach Maa |
| 3 Re-prove loop | substrate back but operability unproven | fresh capture + benign action acknowledgement |
| 4 Runtime-safe recovery | workflow progress failed despite healthy substrate | navigate to known-safe page, re-enter app state |
| 5 Incident quarantine | repeated Level 4 failure or unexplained oscillation | incident bundle, stop and escalate outward |

## Event Schema

### Canonical streams

Two append-only NDJSON streams share the same envelope:
- `tooling` — what the substrate did
- `runtime` — why we asked and whether the workflow moved

### Required envelope

```json
{
  "ts": "2026-03-25T18:41:09.812Z",
  "event_id": "evt-01HQ...",
  "stream": "runtime",
  "kind": "action_ack",
  "name": "tap_ack",
  "session_id": "sess-20260325-1840-001",
  "serial": "127.0.0.1:21503",
  "component": "runtime.verifier",
  "ok": true,
  "readiness_tier": "degraded",
  "degradation_codes": ["preferred_stack_missing"]
}
```

### Strongly recommended identifiers

- `transport_session_id` — substrate attach instance
- `workflow_run_id` — one workflow execution attempt
- `action_id` — one semantic action attempt
- `attempt_id` — retry instance under the same `action_id`
- `frame_before_ref` / `frame_after_ref` — for frame-verified actions
- `frame_before_hash` / `frame_after_hash`

### Required event families

Tooling stream: `bootstrap`, `health_transition`, `heartbeat`, `frame_capture`, `input_dispatch`, `recovery_step`, `incident`, `session_end`

Runtime stream: `session_start`, `observation`, `action_ack`, `workflow_progress`, `incident`, `session_end`

### Example action acknowledgement event

```json
{
  "ts": "2026-03-25T18:41:09.812Z",
  "event_id": "evt-01HQ...",
  "stream": "runtime",
  "kind": "action_ack",
  "name": "tap_ack",
  "session_id": "sess-20260325-1840-001",
  "action_id": "act-00041",
  "attempt_id": "act-00041-attempt-01",
  "serial": "127.0.0.1:21503",
  "component": "runtime.verifier",
  "ok": true,
  "semantic_action": "collect_commission_reward",
  "primitive_action": "tap",
  "coords": [1118, 642],
  "expected_ack": "reward_modal_disappears",
  "ack_result": "confirmed",
  "frame_before_ref": "data/artifacts/sessions/.../00041-before.png",
  "frame_after_ref": "data/artifacts/sessions/.../00042-after.png",
  "frame_before_hash": "sha256:...",
  "frame_after_hash": "sha256:...",
  "dur_ms": 611
}
```

## File Layout

```
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
```

Retention defaults:
- events: 180 days, gzip after 24h
- logs: 14 days success / 30 days failed
- artifacts: 14 days success / 90 days failed; incidents kept indefinitely

## Implementation Phases

### Phase 1 — Fix truthfulness at transport layer

- replace `PASS/FAIL` doctor with 3-tier readiness + degradation codes
- expose per-layer statuses independently in `DoctorReport`
- add structured tooling events under `data/events/tooling/`

### Phase 2 — Runtime heartbeat and action acknowledgement

- separate runtime event writer from tooling event writer
- per-action `action_id` and `attempt_id`
- before/after frame references on meaningful actions
- acknowledgement verifier with expected vs actual verdict
- workflow no-progress watchdog

### Phase 3 — Incident bundles and production gate

- incident bundling across both streams
- promotion gate requiring: stable preferred stack + fresh-frame proof + action acknowledgement + watchdog + one forced-failure drill

## Most Important Near-Term Assertion

The first live assertion this repo should add is:

> if ADB is healthy, Maa/ADB fallback can capture fresh frames, and inputs work, then the system is `degraded`, not `fail`.

That one assertion fixes the conceptual bug from the 2026-03-25 probe run and gives the next runtime slice a truthful foundation.
