# Local Model Serving Quickstart

This document is the operator quickstart for the local model stack.

It answers four practical questions:

- which model to use
- when to use a different model
- how to start local serving
- how to hit the endpoint

## Default Recommendation

Use `qwen35-35b` unless you have a specific reason not to.

It is the strongest default local model in the live config:

- best overall reasoning
- vision-capable
- good fit for OCR, screen interpretation, and harder judgment calls

Use `qwen35-9b` when you want the safest everyday balance of speed, quality,
and VRAM headroom.

## When To Use Which Model

- `qwen35-35b`
  - default for hard cases
  - best for adjudication, ambiguous screens, and general multimodal reasoning

- `qwen35-9b`
  - default for routine work
  - best general-purpose balance for observation and OCR-heavy tasks

- `qwen35-4b`
  - lower-cost multimodal option
  - useful when latency matters more than peak quality

- `qwen35-2b`
  - lightweight multimodal option
  - useful for cheap first-pass observation or quick triage

- `qwen35-08b`
  - cheapest multimodal option
  - use only when low latency matters more than accuracy

- `qwen35-27b`
  - text-only fallback
  - useful only when you want a text model and do not need vision

- `fara-7b`
  - web UI agent model
  - use for browser-style UI interaction experiments

- `ui-tars-7b`
  - UI agent model
  - use for app or interface action planning experiments

- `jedi-7b`
  - GUI grounding specialist
  - use for interface localization and 1080p-style grounding tasks

- `hauhaucs-35b`
  - uncensored Qwen3.5-35B variant
  - not the default because benchmark notes already show a bad game-ID miss

- `qwen3-vl-30b`
  - incomplete in the current config
  - do not use for vision until its `mmproj` is actually present

## State Cartographer Task Map

- `observation`
  - start with `qwen35-9b`
  - use `qwen35-35b` when the screen is ambiguous or the cheaper pass is weak

- `OCR`
  - start with `qwen35-9b`
  - move to `qwen35-35b` for harder extraction or low-confidence cases

- `grounding`
  - use `jedi-7b` for grounding-specific experiments
  - use `qwen35-35b` when grounding depends on broader multimodal reasoning

- `adjudication`
  - use `qwen35-35b`

- `cheap triage`
  - use `qwen35-2b` or `qwen35-08b`

- `UI agent experiments`
  - use `fara-7b` or `ui-tars-7b`

## Start Local Serving

The repo uses `llama-swap` as a single OpenAI-compatible front door. It starts
the matching `llama-server` backend when a request names a model.

Start it with:

```powershell
D:\LocalLargeLanguageModels\llama-swap.exe --config D:\LocalLargeLanguageModels\llama-swap\config.yaml --listen localhost:18800
```

Important live-config assumptions:

- `--parallel 1` is required to avoid wasting KV VRAM
- `--reasoning auto` is enabled for Qwen3.5
- `--flash-attn on` is enabled
- `--no-context-shift` is enabled

## Endpoint

Use the standard OpenAI-compatible chat endpoint:

`http://localhost:18800/v1/chat/completions`

Pick the model with the `model` field in the JSON request body.

## Text Example

```powershell
curl http://localhost:18800/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{
    "model": "qwen35-9b",
    "messages": [
      { "role": "user", "content": "Summarize the current screen state." }
    ]
  }'
```

## Vision Example

Use OpenAI-style multimodal message content when sending an image:

```powershell
curl http://localhost:18800/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{
    "model": "qwen35-35b",
    "messages": [
      {
        "role": "user",
        "content": [
          { "type": "text", "text": "Describe the UI state and list actionable controls." },
          { "type": "image_url", "image_url": { "url": "file:///C:/path/to/screenshot.png" } }
        ]
      }
    ]
  }'
```

If the local stack does not accept `file:///` URLs in your client path, convert
the image to a transport the client supports and keep the request shape the
same.

## Known Caveats

- Do not change `--parallel 1` unless you explicitly want more KV-slot VRAM use.
- Do not rely on Qwen3-VL-30B vision until the missing projector is installed.
- Do not try the broken KV-cache quantization path for Qwen3.5 on the current build.
- `hauhaucs-35b` is available, but it is not the trusted default.

## Source Of Truth

- `D:\LocalLargeLanguageModels\llama-swap\config.yaml`
- `docs/vlm/VLM-overview.md`
- `docs/vlm/VLM-model-profiles.md`
