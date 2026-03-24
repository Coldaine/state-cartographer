# Testing Strategy

TBD — Rewrite required.

The current test suite has evolved organically and doesn't follow the layered structure described in earlier versions of this document. The project has shifted from a Claude Code plugin architecture to an automation runtime with ALAS integration.

When rewritten, this document should describe:
- Unit tests for scripts/ (pytest)
- Integration tests for ALAS bridge components
- Corpus-based validation for observation anchors
- End-to-end tests for executor workflows

See tests/ for current ad hoc test coverage.
