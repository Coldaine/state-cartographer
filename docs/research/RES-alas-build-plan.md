# ALAS State-Machine Build Plan

This document is the execution plan for building the actual state machine from
ALAS. It is not the repo roadmap, and it is not a skill/agent playbook. It is
the concrete work program for converting the live ALAS system into repo-owned
state-machine artifacts and runtime.

## Problem Statement

The repo currently has a page graph:

- states
- transitions
- deterministic transition actions such as `adb_tap`

That is necessary, but incomplete.

ALAS also has:

- assignable scheduler commands/tasks
- a real emulator action surface
- recovery logic
- live execution loops
- task-specific navigation and handling logic

If we stop at `graph.json`, we only model the page-navigation layer. We do not
yet model what the automation can be assigned to do, how those assignments map
onto graph regions, or how real emulator actions are executed and recorded.

## Current Gap

What exists:

- graph schema for states and transitions
- ALAS-derived Azur Lane graph
- session state tracking
- ADB bridge
- observation and locate tools

What is missing:

- canonical inventory of assignable ALAS commands/tasks
- canonical inventory of ALAS emulator actions
- event log of actual executed actions
- mapping from assignment -> required states -> transition plan -> completion
- runtime takeover loop that can run assignments end to end

## Build Objective

Produce a repo-owned state-machine stack with five connected layers:

1. `assignment inventory`
2. `action inventory`
3. `state graph`
4. `execution event log`
5. `assignment runner / takeover runtime`

Each layer must be derivable from ALAS, testable locally, and usable without
wrapping ALAS itself as the final product runtime.

## Workstreams

### 1. Assignment Inventory

Goal:

- enumerate every assignable ALAS scheduler command/task
- record where it is defined
- group it by automation domain

Required output:

- repo-owned JSON inventory of commands/tasks
- each entry includes command name, category, source module, and scheduler
  presence

Examples of categories:

- lifecycle
- campaign/event combat
- operation siren
- rewards/freebies
- shops
- dorm/guild/social
- training/development
- special event modes
- maintenance/daemon tools

### 2. Action Inventory

Goal:

- enumerate the actual emulator actions ALAS performs
- separate primitive device actions from higher-level semantic UI actions

Required output:

- primitive action inventory
- semantic action inventory
- hook-point map for instrumentation

Primitive examples:

- screenshot
- tap
- multi-tap
- long-press
- swipe
- drag
- key event
- app start
- app stop
- hierarchy dump

Semantic examples:

- goto main
- goto page
- confirm popup
- cancel popup
- dismiss announcement
- claim reward
- skip story
- withdraw
- continue auto-search

### 3. Recording Layer

Goal:

- record every real action ALAS performs through the emulator
- record both semantic intent and primitive device action

Required output:

- append-only NDJSON or JSONL event log
- screenshots before/after when available
- state before/after when known

Minimum event schema:

- `ts`
- `run_id`
- `serial`
- `assignment`
- `semantic_action`
- `primitive_action`
- `target`
- `coords` or gesture payload
- `package`
- `screen_before`
- `screen_after`
- `state_before`
- `state_after`
- `ok`
- `duration_ms`
- `error`

Instrumentation targets:

- `vendor/AzurLaneAutoScript/module/device/control.py`
- `vendor/AzurLaneAutoScript/module/device/app_control.py`
- `vendor/AzurLaneAutoScript/module/device/screenshot.py`
- `vendor/AzurLaneAutoScript/module/ui/ui.py`

### 4. Graph Extension

Goal:

- connect assignment semantics to the existing page graph

The current graph captures:

- page/state identity
- transition adjacency
- deterministic movement actions

The next layer must capture:

- which assignments require which entry states
- which assignments can start from unknown state
- which assignments terminate in known recovery states
- which assignments can be resumed
- which assignments are irreversible or expensive

Likely repo-owned extension:

- assignment descriptors separate from `graph.json`
- optional per-assignment metadata:
  - `entry_states`
  - `goal_states`
  - `recovery_strategy`
  - `resume_supported`
  - `requires_live_vision`
  - `estimated_cost`

This should remain separate from the raw page graph unless the schema proves it
must be embedded.

### 5. Takeover Runtime

Goal:

- execute assignments from the repo runtime instead of relying on ALAS as the
  operator

Required runtime behavior:

- start from uncertain or known state
- locate current page
- plan route to assignment entry state
- execute deterministic transitions
- observe and confirm after each action
- recover on unexpected pages
- continue until assignment completes or escalates

This runtime should consume:

- assignment inventory
- action inventory
- graph
- live observations
- session state
- action event log

## Execution Order

### Phase A. Inventory

- extract ALAS commands/tasks
- extract ALAS action surface
- freeze both as repo-owned inventories

### Phase B. Logging

- instrument action execution
- emit structured event logs from live runs
- verify the logs against a real emulator session

### Phase C. Assignment Model

- define assignment schema
- map each ALAS command to assignment metadata
- connect assignments to graph entry and recovery states

### Phase D. Runner

- build a repo-owned assignment runner
- execute a narrow safe subset first
- confirm transition history and recovery behavior

### Phase E. Takeover

- select a small set of assignments
- run them end to end from the repo runtime
- compare repo behavior to ALAS behavior
- expand coverage assignment by assignment

## First Implementation Slice

The first slice should be small and irreversible in value:

1. build `alas command inventory` extractor
2. build `alas action inventory` extractor or doc-backed inventory
3. add a stable event log schema
4. run one live assignment and record its actions

This gives the project:

- command surface
- action surface
- logging surface

Without this, "building the state machine" will keep collapsing into ad hoc page
graph work.

## Immediate Deliverables

The next concrete deliverables are:

1. `scripts/alas_command_inventory.py`
2. tests for that extractor
3. an action-surface inventory artifact or extractor
4. an execution-log schema doc
5. one live recorded run against the emulator

## Done Criteria

This workstream is not done when we merely have a page graph.

It is done when:

- assignments are enumerated
- actions are enumerated
- live action events are recorded
- assignments are mapped onto graph behavior
- the repo can execute at least one assignment end to end without ALAS acting as
  the operator
