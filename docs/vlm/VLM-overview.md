# VLM Overview

> Historical note: this bucket consolidates material that was previously scattered across observation docs and split prompt docs.

## Purpose

`docs/vlm/` is where the repo defines how it uses multimodal models.

This bucket owns:

- model profiles
- task contracts
- context-packing policy
- structured-output expectations
- prompt policy
- local/remote adjudication patterns

## Current Role

VLM is a first-class capability area.

It is not just a helper for page classification. In this repo it potentially supports:

- substate classification
- OCR-heavy extraction
- element grounding
- frame comparison
- disagreement adjudication
- workflow-context reasoning

## Current Code Reality

The surviving active code is still script-shaped and limited:

- `scripts/vlm_detector.py` is an offline tool
- structured contract design is still being clarified
- the repo is not yet using a fully re-earned runtime observation pipeline

## Design Direction

- local multimodal models should do the cheap, frequent work
- stronger remote models should handle difficult adjudication and harder reasoning
- multi-image context should be normal when ambiguity demands it
- task schemas and model profiles should be explicit
- prompts should be thin compared to the rest of the inference stack
