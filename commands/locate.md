# Locate Current State

Determine the current state of the external system by evaluating observations against the state graph.

## Instructions

1. Identify the active graph file (usually `graph.json` in the working directory or `examples/` folder).
2. Gather observations from the current screen/system state.
3. Run the locator:
   ```
   python scripts/locate.py --graph <path-to-graph.json> --observations <observations.json>
   ```
4. Interpret the result:
   - **definitive**: High confidence — proceed with this state.
   - **ambiguous**: Multiple candidates — execute the suggested probes to disambiguate.
   - **unknown**: No match — the system may be in an unmapped state.
