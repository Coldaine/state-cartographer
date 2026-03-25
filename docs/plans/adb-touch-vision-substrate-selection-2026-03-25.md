# ADB Touch/Vision Substrate Selection Plan — 2026-03-25

Status: tactical decision and rollout plan.

This document re-runs the control-substrate question on purpose after the first live MEmu probe and the follow-on capture confusion.

It exists because the repo needed one sharp answer to this question:

**What existing tool stack should own touch + vision over one pinned Android emulator session, and what tiny amount of repo code is still justified above it?**

## Decision status

This document records the **recommended current substrate posture**.

It is intentionally stronger than a vague brainstorm and intentionally weaker than a permanent once-and-for-all proof.

What is directly proven today:
- pinned-device ADB reachability on the current MEmu machine
- repeated screenshot capture and primitive input on that machine
- `scrcpy` usefulness as operator/debug visibility on that machine
- the need to separate transport truth from preferred-stack availability

What is not yet equally proven:
- long-run burn-in stability for the preferred Maa-native posture
- a final Maa-native install/configuration carrying the whole loop without repo fallback
- repeated side-by-side live superiority proof across every shortlisted tool

So this should be read as:

**best current operating posture for this repo and machine, with explicit proof gaps still named.**

See also:
- [agent-control-tool-requirements.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/agent-control-tool-requirements.md)
- [borrowed-control-tool-setup.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/borrowed-control-tool-setup.md)
- [health-heartbeat-logging.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/health-heartbeat-logging.md)
- [testingADB.md](/mnt/d/_projects/MasterStateMachine/docs/dev/testingADB.md)
- [2026-03-25-memu-transport-probe-results.md](/mnt/d/_projects/MasterStateMachine/docs/memory/2026-03-25-memu-transport-probe-results.md)

## Why this plan exists

The repo did successfully connect to MEmu.
What went wrong was not transport reachability.
What went wrong was:

- health classification was too strict and misleading
- capability discovery was conflated with transport truth
- blank or black observations were treated as connection failures
- we spent energy poking custom capture paths before exhausting existing substrate options and documentation

That is a tooling-selection and health-model problem, not proof that the emulator path was unreachable.

## Non-goal

This document does **not** reopen the whole runtime architecture.
It only settles the borrowed touch/vision substrate and the minimal repo-owned glue above it.

## Research method

Candidate discovery used:
- web search for current Android/emulator automation tools and emulator capture failure reports
- local shallow clones under `build/tool-evals/`
- direct read-through of candidate READMEs and capability docs
- repo-specific evaluation against the actual requirement: **one pinned MEmu 9 instance, Unity-first game UI, AI-agent control, local-only operation**

Locally cloned candidate repos:
- `MaaMCP`
- `MaaFramework`
- `uiautomator2`
- `appium-uiautomator2-driver`
- `scrcpy`
- `py-scrcpy-client`
- `minicap`
- `minitouch`
- `AndroidViewClient`
- `Maestro`

## The ten candidates and verdicts

| Candidate | Fit for Unity-first game UI | Observation path | Input path | Evidence level | Maintenance signal | Verdict |
|---|---|---|---|---|---|---|
| `MaaMCP` | strong | screenshot + OCR + pipeline mode | click/swipe/text/key | repo/docs review + indirect live alignment | active | **recommended current primary agent-facing surface** |
| `MaaFramework` | strong | multiple screenshot methods, image-first | multiple input methods | repo/docs review + indirect live alignment | active | **recommended underlying engine** |
| `scrcpy` | medium | live video mirror, excellent operator view | HID-style control | pinned-machine live proof | active | **accept as debug/operator visual aid only** |
| `py-scrcpy-client` | medium | wrapper around scrcpy stream | wrapper around scrcpy control | repo/docs review | maintained | helper only |
| `AndroidViewClient` | limited | screenshot + hierarchy tooling | coordinate and view actions | repo/docs review | active enough | helper/diagnostic only |
| `uiautomator2` | weak for game UI | hierarchy/XML-first | element and coordinate actions | repo/docs review | active | helper/diagnostic only |
| `Maestro` | medium for app testing, weak for this game core | screenshots and assertions | YAML flow actions | repo/docs review | active | not primary for runtime substrate |
| `appium-uiautomator2-driver` | weak for Unity gameplay | WebDriver/hierarchy-centric | WebDriver actions | repo/docs review | active | reject for primary substrate |
| `minicap` | partial only | legacy lossy capture daemon | none | repo/docs review | stale | reject |
| `minitouch` | partial only | none | legacy input daemon | repo/docs review | stale | reject |

## What was actually proven vs inferred

### Directly proven on the pinned Windows + MEmu setup

- ADB transport reachability
- repeated screenshot capture through the accepted path
- primitive input dispatch through the accepted path
- reconnect/recovery smoke path
- `scrcpy` attach and debug usefulness, but not runtime-consumable frame use

### Strongly inferred from candidate code/docs plus fit analysis

- Maa remains the best match for a Unity-first, image-driven substrate
- hierarchy-first stacks should not own gameplay semantics here
- `minicap`/`minitouch` are the wrong modernization target

### Still awaiting explicit live proof

- final Maa-native ownership of the whole loop on this machine
- long-run burn-in stability
- non-trivial text input proof beyond smoke-level success
- repeated-session proof across cold boot, warm attach, and forced reconnect

## Why Maa wins

### 1. It matches the actual problem shape

This repo is not automating a typical native Android app.
It is targeting a Unity-first game where accessibility trees and XML hierarchies are, at best, helper signals.

That makes image-first automation the correct default posture.

Evidence from the candidate set:
- `MaaMCP` explicitly exposes screenshot, OCR, click, swipe, key, and pipeline monitoring to an AI assistant
- `MaaFramework` is explicitly an image-recognition black-box automation framework with multiple capture and input modes
- `uiautomator2` and Appium are explicitly UiAutomator / XPath / XML-centered

### 2. It already aligns with the successful live probe

The first real session already proved:
- ADB serial reachability worked
- fallback control worked
- screenshot capture worked well enough to prove the loop
- `scrcpy` attached but was only suitable as debug/operator visibility on this Windows setup

So the selection result is not theoretical.
It is a formalized version of what the live probe already said once the health misclassification was corrected.

### 3. It keeps our code where it belongs

The repo should own:
- pinned serial and config selection
- readiness classification and degradation codes
- event logging and evidence persistence
- action planning and workflow verification above the substrate

The repo should **not** own:
- custom screenshot backends unless a proven Maa gap exists
- custom touch injection stacks unless Maa cannot cover the requirement
- ad hoc attempts to replace scrcpy or Maa with one-off capture experiments

In short: borrow the hard substrate, own the policy and evidence.

## Why the other candidates lose

### `scrcpy`

`scrcpy` is excellent, but it is a mirror/control tool first.
On this Windows + MEmu setup it is not yet a trustworthy runtime frame API.
It stays valuable as:
- operator visibility
- debug recording
- manual supervision aid

It does not become the semantic runtime owner.

### `uiautomator2` and `appium-uiautomator2-driver`

These are good native-app testing tools.
They are not the right primary substrate for a Unity-rendered game.

Use them only for:
- launcher/system surfaces
- native permission dialogs
- helper diagnostics when hierarchy is available

### `Maestro`

Maestro is attractive for end-to-end app testing, but the repo is not trying to author YAML-first UI test flows as the substrate.
It may still be useful for cross-checks or highly scripted non-game surfaces.
It is not the best fit for the runtime core.

### `minicap` and `minitouch`

These are legacy split-surface daemons.
They fail the practical test here:
- incomplete on their own
- operationally dated
- extra Android 10+ caveats
- poor fit as a modern single-substrate choice

Do not build a new castle on a pair of historical sockets.

## Recommended current decision

### Primary substrate

Use **`MaaMCP` over `MaaFramework`** as the recommended current agent-facing touch/vision surface.

This means:
- the preferred control surface is Maa, not raw ad hoc CLI wrappers
- image-first observation remains the default
- the repo builds runtime intelligence above Maa instead of rebuilding transport below it

This should not be misread as “every Maa-native proof step is already complete”.
It means the repo should now converge on Maa rather than reopen substrate shopping every time the health model lies.

### Accepted degraded mode

If native Maa pieces are partially unavailable but ADB-backed Maa or repo fallback still proves the observe/act loop, classify the system as:
- `operable`
- with explicit degradation codes

Do **not** classify that as generic transport failure.

### Debug visual posture

Use **`scrcpy` as debug/operator visual aid only** unless and until the repo proves a repeatable programmatic frame path on this exact Windows setup.

### Helper tools

Keep these available as helper tools only:
- `uiautomator2`
- `AndroidViewClient`
- optionally `Maestro` for non-game surfaces

Do not let helper tools silently become the primary substrate.

## Windows + MEmu + Unity risks that stay open

- ADB serial drift if emulator instance or port mapping changes
- render-backend or GPU-mode changes causing black, blank, or stale observation
- `scrcpy` coexistence overhead during sustained capture/control loops
- Unity animation causing naive frame-hash freshness checks to lie
- native Android overlays still appearing outside the Unity gameplay layer
- coordinate drift from resolution, DPI, orientation, or window-state changes
- IME/text-input edge cases not yet proven beyond smoke-level success

## Rollout plan

### Phase 1 — stop digging

1. Stop experimenting with custom capture/control code unless a specific Maa gap is proven.
2. Keep the in-repo transport layer thin and explicitly subordinate to borrowed tools.
3. Fix health taxonomy so working fallback posture is reported truthfully.
4. Persist structured tooling evidence for every attach/capture/input/recovery step.
5. Explicitly document which current fallback code is transitional and which is blessed minimal glue.

### Phase 2 — formalize Maa-first runtime posture

1. Install and configure the preferred Maa path cleanly on the pinned machine.
2. Add explicit degraded-mode reporting when the preferred stack is absent but fallback remains operable.
3. Keep `scrcpy` attached only as debug/operator stream.
4. Add before/after capture references to every action attempt.
5. Prove one non-empty text-input path or downgrade text confidence claims.

### Phase 3 — build the runtime above the substrate

1. Add workflow-level action acknowledgement and progress heartbeat.
2. Add incident bundles joining tooling logs and runtime logs.
3. Prove the loop on one safe live workflow before any semantic cache expansion.

## What repo code is still justified

The repo still needs code, but only in the thin layer that existing tools do not own cleanly.

That justified code is:
- config loading and pinned-device selection
- truthful readiness classification
- structured event persistence to local files
- action correlation ids, session ids, and artifact references
- runtime verification logic above primitive clicks and captures
- workflow-specific recovery policy

The repo does **not** need to compete with Maa, scrcpy, or UiAutomator at the transport layer.

## Immediate next actions

1. Implement the readiness/degradation model from [health-heartbeat-logging.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/health-heartbeat-logging.md).
2. Install and validate the preferred Maa-native posture on the pinned MEmu machine.
3. Add live integration tests from [testingADB.md](/mnt/d/_projects/MasterStateMachine/docs/dev/testingADB.md).
4. Treat `scrcpy` as optional debug visibility until a runtime-consumable frame path is proven locally.

## Success condition

This plan is satisfied when the repo can honestly say:

- one pinned MEmu instance is reachable
- Maa-backed touch and vision are the primary substrate
- degraded posture is reported truthfully instead of as blanket failure
- every action leaves behind local file evidence
- workflow-level automation sits above borrowed tools instead of replacing them

For a stronger “final-final” decision, require repeated proof across cold boot, warm attach, and forced reconnect runs.
