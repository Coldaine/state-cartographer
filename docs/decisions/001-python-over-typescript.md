# ADR-001: Python as Primary Runtime Language

## Status: Proposed (pending spike validation)

## Context

The state-cartographer needs a primary runtime language for its scripts (`locate.py`, `pathfind.py`, `session.py`, etc.). The two strongest candidates are:

- **Python**: richer ML/automation ecosystem, most AI agent tooling is Python, pytransitions and python-statemachine are both Python, action execution backends (ADB, Playwright bindings, subprocess) are Python-native
- **TypeScript**: XState is the most complete statechart implementation, growing AI agent ecosystem with Vercel AI SDK

## Decision

**Python** as the primary runtime, with the option to use XState's JSON format as an interchange format.

## Rationale

- Most AI agent automation tooling (ADB wrappers, Playwright Python, image processing) is Python
- pytransitions has the richest introspection API in Python
- python-statemachine 3.0 (Feb 2026) adds compound/parallel states, diagram export, and async support
- imagehash (perceptual hashing for screenshot anchors) is Python
- The plugin targets Claude Code which is language-agnostic but the scripts need a language

## Consequences

- Graph definitions will be JSON (loadable from any language)
- Scripts will be Python 3.11+
- Dependencies: transitions, Pillow, imagehash
- TypeScript/XState can still be used for visualization via Stately Studio

## Open Questions

- Should we validate pytransitions vs python-statemachine in a spike before committing?
- The revisions doc flags this as premature — the spike should be Sprint 1 priority
