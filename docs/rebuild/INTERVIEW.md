# Rebuild Interview

This document is the next step after the peel-back.

No new runtime architecture should be authored until these questions are answered explicitly.

## 1. Problem Statement

- What is the first real capability we are trying to ship?
- Is the first deliverable a labeling system, a supervised runtime, a live observer, or something else?
- What proof would count as success?

## 2. Truth Sources

- Which artifacts are treated as trusted truth right now?
- Which truth sources are weak, inferred, or provisional?
- What existing labeled corpus should be considered gold versus weak labels?

## 3. Agent Instruction

- What is the agent actually instructed to do?
- Where does that instruction live?
- What counts as success, partial success, failure, and escalation?

## 4. First Deliverable

- What is the smallest end-to-end capability worth rebuilding first?
- What should be explicitly out of scope?
- What evidence should be captured during that first capability?

## 5. Minimal Architecture

- What is the thinnest architecture that can support the first deliverable?
- Which contracts are required before code is written?
- Which interfaces must be trusted versus experimental?

## 6. Trusted Interfaces

Produce one list only:

- interfaces we trust now
- interfaces we intend to build next
- interfaces that are explicitly deferred

## Expected Output

The rebuild phase should produce:

1. one authoritative problem statement
2. one first deliverable
3. one minimal architecture
4. one explicit assignment contract
5. one list of trusted interfaces only
