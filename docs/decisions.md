# Decision Log

## 2026-03-25: Do NOT fork StarRailCopilot

**Decision:** Do not fork StarRailCopilot at this time.

**Context:**
- Considered forking StarRailCopilot (LmeSzinc's "next gen ALAS") to get working device/transport layer
- StarRailCopilot has 4.1k stars, 2,065 commits, same device module as ALAS
- Same fundamental problem: black screenshots on MEmu OpenGL via ADB screencap
- StarRailCopilot is template-matching-based, would need to replace detection layer anyway
- Forking adds a large, unfamiliar codebase with its own conventions and debt

**Alternatives considered:**
1. Fork StarRailCopilot → rejected (too much surface area, same black screenshot problem)
2. Fork ALAS directly → rejected (50+ modules, 296 Python files, deeply coupled)
3. Import ALAS as library → rejected (runtime dependency on ALAS execution)
4. Port ALAS device module standalone → rejected (164 import dependencies, tightly coupled monolith)

**Current path:**
- Continue with `state_cartographer/transport/` as thin abstraction over adbutils + MaaTouch
- Solve black screenshot problem by testing DroidCast and scrcpy stream as capture methods
- Build VLM runtime layer independently

**Status:** Deferred — revisit if transport layer remains blocker after VLM runtime is functional

---

## Prior Decisions

*(Add prior decisions here as they occur)*
