# Rebuild Interview

> Historical note: this document was previously `docs/rebuild/INTERVIEW.md`.

This document gates future runtime work.

No new live-runtime architecture should be authored until these questions are answered clearly.

## 1. Problem Statement

- What is the first real capability we are shipping?
- What proof would count as success?
- What is explicitly out of scope for that first capability?

## 2. Truth Sources

- Which artifacts are treated as trusted truth right now?
- Which truth sources are weak or provisional?
- Which labels are gold versus weak?

## 3. Agent Instruction

- What is the agent actually being asked to do?
- Where does that instruction live?
- What counts as success, partial success, failure, and escalation?

## 4. Minimal Architecture

- What is the thinnest architecture that can support the first deliverable?
- Which interfaces must be trusted before code is added?
- Which interfaces are explicitly deferred?

## Expected Output

The rebuild phase should produce:

1. one authoritative problem statement
2. one first deliverable
3. one minimal architecture
4. one explicit assignment contract
5. one list of trusted interfaces only
