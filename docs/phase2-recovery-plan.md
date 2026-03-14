# Phase 2 Recovery Plan: Push, PR, and ALAS Ingestion Reality Check

> Update: the first recovery pass has landed in the working tree. The pre-push
> hook and CI lint scope now target first-party paths, `.gitignore` covers the
> obvious local ALAS artifacts, and the highest-impact docs have been aligned.
> Remaining items below should be read as follow-up cleanup and implementation
> work, not as untouched blockers.

## Why this document exists

This document exists because the current Phase 2 work is blocked by a mismatch between:

- the documented plan,
- the live git state,
- the pre-push gate,
- and the newly staged ALAS submodule.

The goal here is not to describe an idealized roadmap. The goal is to record the **verified current state**, explain **why push is failing**, and define a **phased recovery sequence** that gets the repository back to a state where Phase 2 can proceed sanely.

## Verified facts as of 2026-03-14

### Git and branch state

- Current branch: `feature/phase2-alas-conversion`
- Branch status: **local only**
- Open PRs: **none**
- `gh pr status`: no pull request associated with `feature/phase2-alas-conversion`
- `gh pr list`: no open pull requests in `Coldaine/state-cartographer`
- Local `feature/phase2-alas-conversion` currently points at the same commit as `main`

### Working tree state

At the time of writing, the branch is not clean:

- staged: `.gitmodules`
- staged: `vendor/AzurLaneAutoScript` submodule addition/update
- modified: `plan.md`
- modified: `CLAUDE.md`
- untracked: `vendor/alas_req_clean.txt`
- untracked: `vendor/alas_requirements_clean.txt`
- untracked: `vendor/alas_requirements_frozen.txt`

### Push failure

`git push -u origin HEAD` was run and failed.

The failure is **not hypothetical** and **not a remote auth problem**.

The failure is caused by the repo's pre-push hook:

- `.githooks/pre-push` runs `uv run ruff check .`
- `.githooks/pre-push` runs `uv run ruff format --check .`
- those commands recurse into `vendor/AzurLaneAutoScript`
- Ruff reports thousands of violations in vendor code
- push aborts before anything is sent

This is the direct blocker.

### ALAS integration state

- `.gitmodules` points to `vendor/AzurLaneAutoScript`
- the staged submodule commit is `adfe9783b980eee95e318a708c4c297f04934e56`
- the repository currently has a real git submodule path at `vendor/AzurLaneAutoScript`

### Documentation drift

The repo contains multiple stale instructions that materially mislead work:

1. Many docs still reference `plugin/scripts/...` even though scripts live in `scripts/`
2. Many docs still reference `mock.py` even though the file is `scripts/screenshot_mock.py`
3. `AGENTS.md` still says the ALAS submodule is at `external/alas/`
4. `plan.md` describes Phase 2 around `scripts/alas_converter.py`, but that tool does not exist yet
5. `docs/testing-strategy.md` still describes the older plugin-era layout

## Root cause analysis

The current blockage is a combination of three issues:

### 1. Infrastructure and feature work were mixed together

The current branch contains both:

- infrastructure changes for bringing ALAS into the repo as a submodule/reference source, and
- planning/doc changes for Phase 2.

That is workable only if the repo gates already understand vendored or external code. They do not.

### 2. The pre-push gate was written for a smaller repo shape

The existing hook assumes all Python under the repository root is first-party code that should satisfy repo Ruff rules.

That assumption became false the moment `vendor/AzurLaneAutoScript` was staged.

### 3. The docs no longer describe the repo accurately

Because the docs still mix:

- old `plugin/scripts/` paths,
- old `mock.py` naming,
- old ALAS location assumptions,
- and aspirational Phase 2 tooling,

it becomes very easy to think work is farther along than it really is.

## What Phase 2 actually is right now

Phase 2 is **not** currently “conversion in progress.”

Phase 2 is currently **blocked at preparation**. The real status is:

1. The repo has the concept of using ALAS as reference data
2. The repo now has a staged ALAS submodule path
3. The push/PR workflow for that submodule is currently broken
4. The converter described in the plan does not exist yet
5. The example Azur Lane graph is not a complete generated output from ALAS conversion

That means the next work is not “continue Phase 2 feature implementation” in the abstract.

The next work is:

- unblock push,
- clean up doc drift,
- decide and land the ALAS reference strategy,
- then implement the actual converter or an explicitly different Phase 2 ingestion path.

## Recovery strategy

This work should be split into explicit phases.

### Recovery Phase A — Unblock push for vendor paths

**Goal:** allow branches that stage or reference ALAS to push without linting third-party source.

#### Required changes

1. Update `.githooks/pre-push` so Ruff does not lint `vendor/`
2. Update repo lint config so CI and local linting exclude `vendor/` as third-party code
3. Verify tests still run for first-party code

#### Acceptance criteria

- `uv run ruff check .` no longer reports ALAS vendor violations, or the hook scopes Ruff to first-party paths only
- `uv run ruff format --check .` no longer inspects vendor code
- `uv run pytest tests/ -q` still passes
- `git push -u origin <branch>` succeeds on a branch containing the submodule change

#### Why this goes first

Until this lands, every ALAS-related branch is dead on arrival.

### Recovery Phase B — Normalize documentation to current repo reality

**Goal:** stop future agents and humans from following broken instructions.

#### Required fixes

1. Replace `plugin/scripts/` with `scripts/`
2. Replace `mock.py` references with `scripts/screenshot_mock.py` where appropriate
3. Fix ALAS path references from `external/alas/` to the actual chosen location
4. Mark Phase 2 tooling as planned vs implemented
5. Clarify the difference between project milestones and playbook phases where the numbering collides

#### Acceptance criteria

- high-traffic docs (`AGENTS.md`, `plan.md`, `CLAUDE.md`, `docs/testing-strategy.md`) reflect the current repo structure
- skill and agent instructions reference working commands
- no top-level planning doc claims that `scripts/alas_converter.py` exists when it does not

### Recovery Phase C — Decide ALAS reference strategy explicitly

**Goal:** remove ambiguity about whether ALAS is:

- a git submodule,
- an external path configured by the user,
- or a copied vendor tree.

#### Current evidence

- current working state is using a submodule at `vendor/AzurLaneAutoScript`
- historical docs mention `external/alas/`
- `plan.md` has also described a non-submodule path-based approach in places

#### Decision to record

Choose one of the following and document it everywhere:

1. **Submodule strategy**
	- ALAS is pinned as a submodule
	- repo tooling excludes vendor code from linting
	- scripts read from `vendor/AzurLaneAutoScript`

2. **User-provided path strategy**
	- ALAS is not stored in the repo
	- conversion tooling takes `--alas-root`
	- docs remove submodule references entirely

3. **Hybrid strategy**
	- optional submodule for contributors
	- converter still supports `--alas-root`
	- docs clearly separate contributor workflow from end-user workflow

#### Recommended direction

The safest contributor workflow is likely:

- keep optional support for `--alas-root`
- allow a contributor submodule under a documented path
- never lint vendor code as first-party code

### Recovery Phase D — Re-scope actual Phase 2 implementation

**Goal:** make the implementation backlog match the repo instead of the other way around.

#### Phase 2 work items that are still not done

1. `scripts/alas_converter.py`
2. `tests/test_alas_converter.py`
3. generated or calibrated Azur Lane example graph based on real ALAS source data
4. any schema work needed for locale-aware anchors or region-color anchors
5. explicit tests for ALAS-derived transitions and anchor extraction

#### Acceptance criteria

- the plan identifies these as open implementation work
- the repo structure and docs no longer imply they are already present

## Recommended branch and PR strategy

The recovery should be split into small PRs.

### PR 1 — Push gate fix

**Purpose:** unblock all ALAS-related pushes.

**Scope:**

- `.githooks/pre-push`
- Ruff exclusion or scoped lint paths
- minimal related doc note if needed

**Do not include:** Phase 2 converter work.

### PR 2 — Doc reality alignment

**Purpose:** make the repo stop lying to contributors.

**Scope:**

- `AGENTS.md`
- `plan.md`
- `docs/testing-strategy.md`
- skill/rule/agent docs with broken commands

**Do not include:** substantive new feature code.

### PR 3 — ALAS reference strategy

**Purpose:** land the chosen submodule/external-path approach cleanly.

**Scope:**

- `.gitmodules` if submodule is kept
- contributor docs
- any ignore/exclusion updates

### PR 4 — Real Phase 2 implementation

**Purpose:** implement the converter or whatever Phase 2 actually becomes after the above cleanup.

**Scope:**

- converter
- tests
- schema deltas
- example graph generation

## Subagent assignment plan

Subagents should be used selectively.

### Best subagent targets

#### 1. Read-only repo audit

Use a read-only exploration subagent to:

- scan for stale path references
- enumerate doc drift
- verify which files mention old commands

This is high leverage and low risk.

#### 2. Branch/PR strategy audit

Use a read-only exploration subagent to:

- inspect git metadata
- inspect PR state
- recommend branch splits

This is also high leverage.

### What should not be delegated blindly

#### 1. Hook and lint gate changes

These should be implemented carefully in the main lane because they affect repo-wide policy.

#### 2. ALAS strategy decision

This requires human intent, not just file inspection. A subagent can summarize tradeoffs, but the final decision should be explicit.

#### 3. Phase 2 scope definition

Subagents can inventory missing work, but a human or the main lane should decide whether Phase 2 is:

- direct conversion,
- calibration-first,
- or hybrid ingestion.

## Immediate next actions

1. Fix the push gate so vendor code is not linted as first-party code
2. Push a small PR for that fix
3. Land a separate doc-alignment PR
4. Decide whether ALAS remains a submodule at `vendor/AzurLaneAutoScript` or moves to a different documented strategy
5. Only after that, start the actual Phase 2 converter/integration work

## Non-goals for this recovery doc

This document does **not** assume:

- that a PR already exists,
- that Phase 2 implementation is underway,
- that the Azur Lane example graph is fully generated,
- or that current docs are trustworthy.

It assumes only what has been verified from the live repo state.
