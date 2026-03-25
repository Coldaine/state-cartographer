# Documentation Playbook

## Purpose

This document explains how documentation is supposed to work in this repo.

It is the procedural companion to the repo indexes. Use it when you need to add, move, split, or clean up docs without creating overlap or drift.

See also:
- [AGENTS.md](/mnt/d/_projects/MasterStateMachine/AGENTS.md)
- [docs/AGENTS.md](/mnt/d/_projects/MasterStateMachine/docs/AGENTS.md)
- [architecture-overview.md](/mnt/d/_projects/MasterStateMachine/docs/architecture-overview.md)
- [repo-index.md](/mnt/d/_projects/MasterStateMachine/docs/repo-index.md)

## Core Rule

`docs/` is the project knowledge layer.

Use it for persistent project knowledge, not for implementation code. Keep documentation organized around the question it answers, not around the current code layout.

## Domains And Buckets

Only two explicit documentation domains remain:

- `ALS-reference/`
- `RES-research/`

Everything else in `docs/` is a knowledge bucket rather than a domain.

Current buckets include:

- `todo.md`
- `memory/`
- `prework/`
- `runtime/`
- `vlm/`
- `plans/`
- `workflows/`
- `agentPrompts/`

Do not create a new domain unless the repo has explicitly decided to promote one.

## How To Choose The Right Home

Before adding a doc, answer:

- what exact question does this doc answer?
- which existing doc is closest?
- why can that existing doc not absorb the change?
- what overlap risk does this placement create?

If those answers are weak, the doc probably should not be added.

Use these placement rules:

- put the repo-wide execution tracker in `docs/todo.md`
- put repo-wide status and orientation docs directly under `docs/`
- put dated lessons and preserved findings in `docs/memory/`
- put corpus preparation and cleanup procedures in `docs/prework/`
- put runtime contracts and live-system boundaries in `docs/runtime/`
- put model-family guidance and task contracts in `docs/vlm/`
- put workflow/task descriptions in `docs/workflows/`
- put code-linked prompt rationale docs in `docs/agentPrompts/`

If a doc is narrow, put it next to the question it answers instead of creating a new top-level category.

## Repo-Wide Todo Rule

`docs/todo.md` is allowed as the single repo-wide execution tracker.

Its purpose is operational, not architectural.

It should contain:

- current focus
- active checklist items
- blockers
- deferred items when useful

It should not contain:

- duplicated architecture rationale
- duplicated near-term plan narrative
- long-form design explanation already owned by another doc
- historical memory that belongs in `docs/memory/`

Use these boundaries:

- `docs/todo.md` owns current truth, execution tracking, and the near-term change program
- canonical plan docs own architecture and rationale

## One Question, One Owner

Prefer one authoritative doc per question.

Do not create multiple docs that answer the same question in slightly different words. If a new document is necessary, define its boundary against neighboring docs immediately.

Use these existing ownership boundaries:

- `todo.md` owns current truth, repo-wide execution tracking, and the near-term change program
- `north-star.md` owns desired end state
- `architecture-overview.md` owns the organizing model for the repo
- `repo-index.md` owns the exhaustive repo map
- `docs/AGENTS.md` owns fast navigation inside `docs/`
- `documentation-playbook.md` owns documentation workflow rules

## What To Update When Docs Change

When a new doc changes the repo map or the docs map, update the indexes that point people to it.

At minimum, check:

- [docs/AGENTS.md](/mnt/d/_projects/MasterStateMachine/docs/AGENTS.md)
- [repo-index.md](/mnt/d/_projects/MasterStateMachine/docs/repo-index.md)

Also update these when applicable:

- [architecture-overview.md](/mnt/d/_projects/MasterStateMachine/docs/architecture-overview.md) if the new doc changes how the docs tree should be understood
- [AGENTS.md](/mnt/d/_projects/MasterStateMachine/AGENTS.md) if the new doc is a repo-level entrypoint

Do not add or move docs and leave the indexes stale.

Use this tighter default:

- update `docs/AGENTS.md` and `repo-index.md` by default when docs placement or ownership changes
- update root `AGENTS.md` only when something becomes true repo-level entrypoint material or required reading
- do not add ordinary docs-map changes to root `AGENTS.md` just because a new doc exists

## Prompt-Bearing Code Rule

Any code that contains an LLM prompt must have a separate markdown document under `docs/agentPrompts/`.

That companion document must:

- link to the code file that contains the prompt
- justify each meaningful part of the prompt
- explain how each part helps the specific model or agent on that task

Keep file-specific prompt rationale in `docs/agentPrompts/`, not in generic prompt-policy docs.

Use [VLM-prompts.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-prompts.md) for prompt-layer guidance and policy. Use `docs/agentPrompts/` for code-linked prompt justification.

## What To Avoid

- do not create a new doc if an existing doc can absorb the responsibility cleanly
- do not create a new explicit domain beyond `ALS` and `RES`
- do not bury important repo rules only inside scripts or code comments
- do not let indexes drift after adding or moving docs
- do not mix current truth, desired future state, and tactical planning into one document
- do not let `docs/todo.md` turn into a second plan document
- do not let prompt rationale sprawl into unrelated docs

## Maintenance Checklist

Before finishing a documentation change, verify:

- the document has a clear single purpose
- the placement matches the question it answers
- neighboring docs still have clear boundaries
- the relevant indexes point to the new or moved document
- any prompt-bearing code has a matching file in `docs/agentPrompts/`
