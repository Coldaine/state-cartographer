# Validate Graph

Check a graph definition for schema errors, missing fields, and structural issues.

## Instructions

1. Identify the graph file to validate.
2. Run the validator:
   ```
   python scripts/schema_validator.py <path-to-graph.json>
   ```
3. If errors are found, fix them and re-validate.
4. A valid graph has: all states as objects, valid anchor types, valid transition methods, valid confidence thresholds, proper source/dest references, and cost annotations.
