# Pilot Usage Clarity Plan (temporary)

## Why this exists

The repository has a working transport facade (`state_cartographer.transport.Pilot`) and a set of script-shaped utilities under `scripts/`, but there is no single, concise document that tells a new contributor:

- what `Pilot` is for
- how it differs from a CLI
- when to use `scripts/` versus `Pilot`
- whether package installation is required
- what the intended public API surface is

## Evidence collected so far

- `state_cartographer/transport/pilot.py` defines a facade class with methods like `connect()`, `disconnect()`, `screenshot()`, `tap()`, `swipe()`, `keyevent()`, `input_text()`, `health_check()`, and `recover()`.
- `state_cartographer/transport/__init__.py` exports `Pilot` as the recommended transport entry point.
- `pyproject.toml` configures setuptools packaging, but does not define `project.scripts` or console entry points.
- `docs/transport-methods.md` frames `Pilot` as the transport layer choice and distinguishes capture/input methods.
- `docs/todo.md`, `docs/architecture-overview.md`, and `docs/repo-index.md` describe `state_cartographer/transport/` as the transport package and `scripts/` as active tooling.
- `docs/runtime/backend-lessons.md` and `docs/plans/multi-tier-runtime-implementation-plan-2026-03-24.md` describe transport as borrowed substrate for a future runtime, not a standalone CLI app.
- `scripts/vlm_detector.py` states it is an offline VLM labeling helper and explicitly says it is not trusted runtime truth.
- `scripts/stress_test_adb.py` is a validation/debug utility for ADB transport, not a user-facing CLI for the package.

## Likely conclusion

The repo is currently organized as a **Python library package with supporting scripts**, not as a CLI-first application. The library exposes the transport primitives; the scripts are operational tools for testing, labeling, and data collection.

## Proposed fix

Split the work into two tracks:

### Immediate: Pilot usage guide

Create a focused user-facing guide that answers:

1. What `Pilot` is
2. What `Pilot` is not
3. When to use `Pilot` directly
4. When to use `scripts/`
5. How to install and import the package during development
6. What the minimal usage pattern looks like
7. What the public transport API includes
8. What is intentionally excluded
9. How MaaTouch is deployed on the device
10. Where future runtime code should live

### Strategic: packaging / CLI decision

Handle CLI or external publication as a separate follow-up decision if the maintainer wants it.

## Draft deliverables

- `docs/transport-usage.md` as the immediate user-facing guide
- optional smoke test proving the recommended import/install path
- update `docs/repo-index.md` and `docs/architecture-overview.md` only if the new guide creates ambiguity

## Questions to ask the maintainer

1. Is `Pilot` intended as a library-only package, or should we design CLI entry points for automation scripts?
2. What are the development setup expectations: editable install, direct script invocation, or both?
3. For MaaTouch binary deployment, should the guide assume users deploy it manually, or should `Pilot.connect()` handle it automatically?
4. Should the transport usage guide live in `docs/transport-usage.md` or as a README under `state_cartographer/`?
5. Should the transport guide acknowledge the future runtime architecture, or stay purely focused on the current library API?

## Next step

Review the existing docs and code paths, then decide whether to:
- add a concise usage guide
- add CLI entry points
- expand the public facade
- or keep the current split and document it better