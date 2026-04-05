# Prompt Quality Review Instructions

When reviewing pull requests in this repository, apply these checks to any file that contains agent prompts, VLM prompts, or LLM prompt templates.

## Mandatory Checks

### 1. Prompt Justification Registry
Every prompt must be documented in `docs/prompts/prompt-justification.md`. If a PR adds or modifies a prompt and does not update the justification registry, flag it as incomplete.

### 2. Standalone File Policy
Agent definitions (`.agent.md` files, prompt templates loaded at runtime) must be standalone files, not inlined in application code, unless the prompt is in active development and explicitly marked as "inline pending stabilization" in the justification registry.

### 3. Output Schema Enforcement
All prompts that feed into code must:
- Specify JSON output format
- Define exact field names and types
- Instruct the model to use `null` for undetermined fields (not omit them)
- Include a `confidence` field (0.0-1.0) for any classification or detection task

### 4. Prompt-Code Alignment
Check that the fields requested in the prompt match the fields parsed in the code that consumes the response. Mismatches between prompt output schema and `dict.get()` / JSON parsing code are a common source of silent data loss.

### 5. Candidate Constraints
If the prompt asks the model to choose from a known set (page labels, rarity tiers, ship classes), verify that:
- The candidates are passed explicitly in the prompt (not assumed from training data)
- The candidates match the values expected by downstream code (enum values, DB column constraints)

## Quality Signals

### Good Prompts
- Request structured JSON with explicit field list
- Include confidence and rationale fields
- Constrain output space with candidate lists where applicable
- Use null-over-omission policy
- Have a corresponding entry in the justification registry

### Prompts That Need Attention
- Free-text output consumed by code (parsing will be fragile)
- Missing confidence field on classification tasks
- Prompt field names that don't match the code parsing them
- No entry in justification registry
- Hardcoded values that should come from configuration (model names, endpoint URLs)

## Workflow Coherence
When reviewing agent definitions (`.agent.md` files):
- Check that the agent does not self-reference in its `agents:` field (creates recursive handoff)
- Check that file paths in the prompt are repo-relative (not absolute paths like `/memories/...`)
- Check that code examples in the prompt use the current API (e.g., `Pilot` context manager, not deprecated methods)
- Check that the agent's stated capabilities match the tools it declares
