#!/usr/bin/env python3
"""Benchmark screenshot capture methods on Shield TV.

Compares:
1. Raw ADB screencap (baseline)
2. ADB exec-out screencap (mobile-mcp's method)
3. ADB screencap with JPEG conversion on-device
4. ADB screencap at reduced resolution

Run on Pi: python3 benchmark_screenshot.py
"""

import subprocess
import time
import sys
from pathlib import Path

DEVICE = "192.168.0.160:5555"
ROUNDS = 5


def run_adb(*args: str) -> tuple[bytes, float]:
    """Run ADB command, return (stdout_bytes, elapsed_seconds)."""
    t0 = time.monotonic()
    result = subprocess.run(
        ["adb", "-s", DEVICE, *args],
        capture_output=True,
    )
    elapsed = time.monotonic() - t0
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr.decode()[:200]}", file=sys.stderr)
    return result.stdout, elapsed


def benchmark(name: str, fn) -> dict:
    """Run a capture function ROUNDS times, return stats."""
    times = []
    sizes = []
    print(f"\n{'='*50}")
    print(f"Benchmark: {name}")
    print(f"{'='*50}")
    for i in range(ROUNDS):
        data, elapsed = fn()
        times.append(elapsed)
        sizes.append(len(data))
        print(f"  Round {i+1}: {elapsed*1000:.0f}ms, {len(data)/1024:.0f}KB")
    avg_time = sum(times) / len(times)
    avg_size = sum(sizes) / len(sizes)
    min_time = min(times)
    max_time = max(times)
    print(f"  ---")
    print(f"  Avg: {avg_time*1000:.0f}ms | Min: {min_time*1000:.0f}ms | Max: {max_time*1000:.0f}ms")
    print(f"  Avg size: {avg_size/1024:.0f}KB")
    return {"name": name, "avg_ms": avg_time*1000, "min_ms": min_time*1000, "max_ms": max_time*1000, "avg_kb": avg_size/1024}


def method_shell_screencap():
    """adb shell screencap -p (raw shell, binary encoding issues possible)."""
    return run_adb("shell", "screencap", "-p")


def method_execout_screencap():
    """adb exec-out screencap -p (mobile-mcp's method, cleaner binary)."""
    return run_adb("exec-out", "screencap", "-p")


def method_execout_screencap_jpeg():
    """Capture PNG on device, convert to JPEG on device via toybox."""
    # screencap outputs PNG; we pipe through a raw framebuffer + convert
    # Actually screencap -p is always PNG. We can try without -p for raw RGBA.
    return run_adb("exec-out", "screencap", "-p")


def method_screencap_half_res():
    """Reduce display to 960x540, screencap, restore."""
    # Set lower resolution
    subprocess.run(["adb", "-s", DEVICE, "shell", "wm", "size", "960x540"],
                   capture_output=True)
    data, elapsed = run_adb("exec-out", "screencap", "-p")
    # Restore original resolution
    subprocess.run(["adb", "-s", DEVICE, "shell", "wm", "size", "reset"],
                   capture_output=True)
    return data, elapsed


def method_screencap_raw_to_file():
    """screencap to file on device, then pull."""
    t0 = time.monotonic()
    subprocess.run(
        ["adb", "-s", DEVICE, "shell", "screencap", "-p", "/sdcard/bench_shot.png"],
        capture_output=True,
    )
    result = subprocess.run(
        ["adb", "-s", DEVICE, "exec-out", "cat", "/sdcard/bench_shot.png"],
        capture_output=True,
    )
    elapsed = time.monotonic() - t0
    return result.stdout, elapsed


def main():
    print(f"Screenshot Benchmark — Device: {DEVICE}")
    print(f"Rounds per method: {ROUNDS}")

    # Verify device is connected
    data, _ = run_adb("get-state")
    state = data.decode().strip()
    print(f"Device state: {state}")
    if state != "device":
        print("ERROR: Device not connected!")
        sys.exit(1)

    results = []
    results.append(benchmark("1. adb shell screencap -p", method_shell_screencap))
    results.append(benchmark("2. adb exec-out screencap -p (mobile-mcp)", method_execout_screencap))
    results.append(benchmark("3. screencap to file + cat", method_screencap_raw_to_file))
    results.append(benchmark("4. exec-out screencap at 960x540", method_screencap_half_res))

    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"{'='*50}")
    print(f"{'Method':<45} {'Avg':>7} {'Min':>7} {'Max':>7} {'Size':>7}")
    print("-" * 80)
    for r in results:
        print(f"{r['name']:<45} {r['avg_ms']:>6.0f}ms {r['min_ms']:>6.0f}ms {r['max_ms']:>6.0f}ms {r['avg_kb']:>5.0f}KB")

    # Speedup vs baseline
    baseline = results[0]["avg_ms"]
    print(f"\nSpeedup vs baseline (shell screencap):")
    for r in results[1:]:
        speedup = baseline / r["avg_ms"] if r["avg_ms"] > 0 else 0
        print(f"  {r['name']}: {speedup:.2f}x")


if __name__ == "__main__":
    main()
