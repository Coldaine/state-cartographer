# Template Graph

A minimal starter graph definition showing the state-cartographer schema extensions.

## Fields

- **states**: each state has `anchors` (observation signals), `confidence_threshold`, and optional `wait_state`, `negative_anchors` annotations
- **transitions**: each transition has `source`, `dest`, `method` (deterministic/vision_required), `action`, and `cost`

## Usage

Copy this file and modify for your target system. See `docs/architecture.md` Layer 1 for the full schema specification.
