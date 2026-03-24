# 2026-03-24 MEmu `fb0` Capture Proof

## Question

Does direct framebuffer capture on the rooted MEmu 9 instance produce non-black frames for the live Azur Lane session?

## Scope

This note records one direct proof run against the currently configured MEmu instance in this repo:

- serial: `127.0.0.1:21513`
- config reference: `configs/memu.json`
- foreground app at test time: `com.YoStarEN.AzurLane/com.manjuu.azurlane.MainActivity`

This is a preserved finding, not a claim that the repo already has a production capture transport.

## Observed Facts

### 1. Root access exists, but not through `su`

The emulator image does not provide `su`:

- `adb -s 127.0.0.1:21513 shell su -c id`
- result: `/system/bin/sh: su: not found`

But `adbd` can run as root:

- `adb -s 127.0.0.1:21513 root`
- result: `adbd is already running as root`
- `adb -s 127.0.0.1:21513 shell id`
- result: `uid=0(root) ...`

Operationally, the usable root path on this instance is `adb root`, not `adb shell su -c ...`.

### 2. `fb0` is present and readable

Direct framebuffer metadata on the tested instance:

- device: `/dev/graphics/fb0`
- sysfs name: `hyperv_fb`
- virtual size: `1152,864`
- mode: `U:1152x864p-0`
- bits per pixel: `32`
- stride: `4608`

Expected full-frame size from those values:

- `1152 * 864 * 4 = 3981312` bytes

### 3. `exec-out cat /dev/graphics/fb0` was not trustworthy here

A direct `adb exec-out cat /dev/graphics/fb0 > ...` attempt produced a truncated local file:

- observed local size: `3330048` bytes

That does not match the expected frame size, so this path should not be treated as the reliable implementation on this emulator image without additional framing logic.

### 4. On-device `dd` plus `adb pull` produced a complete frame

Reliable capture sequence:

```bash
adb -s 127.0.0.1:21513 root
adb -s 127.0.0.1:21513 shell "dd if=/dev/graphics/fb0 of=/sdcard/fb0_full.raw bs=3981312 count=1"
adb -s 127.0.0.1:21513 pull /sdcard/fb0_full.raw
```

Observed result:

- transferred bytes: `3981312`
- pulled local file length: `3981312`

### 5. The captured frame was not black

Quick inspection of the full raw dump showed:

- `all_zero = False`
- non-zero byte ratio: about `0.0506`
- non-black RGB pixels: `65171` of `995328`

Decoded preview images were generated locally in both RGBA and BGRA channel order during the proof run and both contained visible non-black content.

## Conclusion

Yes: on this MEmu/Azur Lane instance, direct `fb0` capture can produce non-black frames.

The important correction is that the tested image does not support the proposed `su -c` flow. The working root mechanism is:

1. `adb root`
2. read `/dev/graphics/fb0`
3. prefer on-device `dd` plus `adb pull` over naive `exec-out cat`

## Practical Implication

For this emulator image, a minimal root-backed framebuffer transport is plausible.

The most defensible first implementation shape is:

- root bootstrap through `adb root`
- framebuffer metadata read from `/sys/class/graphics/fb0/*`
- full-frame capture through `dd if=/dev/graphics/fb0 ...`
- local decode with explicit channel-order handling
- validation that rejects truncated or near-black frames

## Limits Of This Proof

This proof does not yet establish:

- streaming performance
- stable frame cadence
- whether `minicap` is better than `fb0`
- whether the same result holds on the second visible MEmu serial
- whether repeated capture remains reliable across long sessions

It establishes only that direct framebuffer reads can return a usable non-black frame from the active Azur Lane session on the tested instance.
