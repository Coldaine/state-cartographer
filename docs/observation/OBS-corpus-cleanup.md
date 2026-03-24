# Black-Frame Cleanup

## Purpose

The large observation corpus contains many PNGs that are not low-value in a
subtle way; they are fully black captures produced during MEmu / Unity /
DEX transition periods. These files inflate the corpus and distort quick
inspection because they dominate the capture directories numerically.

This note documents the cleanup rule and the script used to apply it.

## Scope

This cleanup targets the large recorded corpus, not ad hoc screenshots:

- `data/raw_stream`
- `data/alas-observe/**/screenshots`

It is **not** intended for:

- `data/screenshots` ad hoc debugging captures
- `vendor/AzurLaneAutoScript/assets/**`

## Verification Rule

A PNG is treated as a verified black frame only if all of the following are true:

1. file size is `<= 10000` bytes
2. grayscale mean is `<= 5.0`
3. grayscale standard deviation is `<= 2.0`

The size filter is a cheap first pass. In this corpus, fully black PNGs were
consistently tiny, typically around `2759` bytes. The image-stat check is the
actual verification step.

## 2026-03-20 Cleanup Result

A first cleanup pass using this rule removed:

- `6080` files from `data/raw_stream`
- `1726` files from `data/alas-observe`
- `7806` verified black frames total

This was a destructive cleanup after verification, not a quarantine move.

## Script

Use [delete_black_frames.py](D:/_projects/MasterStateMachine/scripts/delete_black_frames.py).

Dry run:

```bash
uv run python scripts/delete_black_frames.py --json
```

Delete verified black frames:

```bash
uv run python scripts/delete_black_frames.py --delete --json
```

Custom roots:

```bash
uv run python scripts/delete_black_frames.py \
  --root data/raw_stream \
  --root data/alas-observe \
  --delete
```

## Why This Exists

The point of this cleanup is not to build a sophisticated quality classifier.
It is to remove the easiest, most obviously useless corpus noise quickly so the
remaining review work focuses on real screenshots, dark-but-meaningful loading
screens, and genuine state-bearing captures.
