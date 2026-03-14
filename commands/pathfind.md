---
name: Find Path
description: Find the cheapest route between two states in the graph using weighted Dijkstra pathfinding.
type: command
usage: /pathfind
---

# Find Path

Find the cheapest route between two states in the graph using weighted pathfinding.

## Instructions

1. Identify the graph file and the source/destination states.
2. Run the pathfinder:
   ```
   python scripts/pathfind.py --graph <path-to-graph.json> --from <start-state> --to <target-state>
   ```
3. Optional flags:
   - `--avoid <state1> <state2>` — exclude specific states from the route
   - `--prefer deterministic` — prefer deterministic transitions over vision-required ones
4. The result includes the path, total cost, and ordered list of transitions to execute.
