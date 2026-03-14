---
name: Graph Info
description: Get a summary of a state graph including total states, transitions, completeness metrics, and potential issues.
type: command
usage: /graph-info
---

# Graph Info

Get a summary of a state graph: total states, transitions, completeness metrics, and potential issues.

## Instructions

1. Identify the graph file.
2. Run the graph summary:
   ```
   python scripts/graph_utils.py --graph <path-to-graph.json> summary
   ```
3. Other available subcommands:
   - `states` — list all state IDs
   - `orphans` — find states with no inbound transitions
   - `missing-anchors` — find states without observation anchors
