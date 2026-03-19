"""
Test DroidCast screenshot stability using ALAS's exact startup approach.
Uses uiautomator2's ATX agent /shell/background endpoint.
"""

import subprocess
import time

import numpy as np
import requests

SERIAL = "127.0.0.1:21513"
DROIDCAST_PORT = 53516
LOCAL_PORT = 0  # Will be assigned by adb forward


def adb(*args):
    cmd = ["adb", "-s", SERIAL, *list(args)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    return r.stdout.strip(), r.returncode


def kill_droidcast():
    """Kill existing DroidCast processes."""
    out, _ = adb("shell", "ps -ef 2>/dev/null || ps")
    for line in out.splitlines():
        if "droidcast_raw" in line.lower() or "ink.mol.droidcast" in line:
            parts = line.split()
            pid = parts[1]
            print(f"  Killing DroidCast pid={pid}")
            adb("shell", f"kill -9 {pid}")
    time.sleep(1)


def remove_forwards():
    """Remove existing port forwards."""
    adb("forward", "--remove-all")


def start_droidcast_via_u2():
    """Start DroidCast using u2 ATX agent's /shell/background endpoint."""
    import uiautomator2 as u2

    ud = u2.connect(SERIAL)

    # Use ATX agent's background shell endpoint (same as ALAS)
    cmd = "CLASSPATH=/data/local/tmp/DroidCast_raw.apk app_process / ink.mol.droidcast_raw.Main > /dev/null"
    resp = ud.http.post("/shell/background", data={"command": cmd, "timeout": "10"}, timeout=20)
    print(f"  ATX background response: {resp.status_code} {resp.json()}")
    return ud


def setup_forward():
    """Set up ADB port forward."""
    out, _rc = adb("forward", "tcp:0", f"tcp:{DROIDCAST_PORT}")
    port = int(out.strip())
    print(f"  Port forward: localhost:{port} -> device:{DROIDCAST_PORT}")
    return port


def wait_startup(port, timeout=10):
    """Wait for DroidCast to come online (404 on / means ready)."""
    session = requests.Session()
    session.trust_env = False
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = session.get(f"http://127.0.0.1:{port}/", timeout=3)
            if r.status_code == 404:
                print("  DroidCast online (404 on /)")
                return session, port
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(0.25)
    print("  WARNING: Startup timeout, proceeding anyway")
    return session, port


def take_screenshot(session, port, idx, endpoint="/preview"):
    """Take a screenshot and report stats."""
    url = f"http://127.0.0.1:{port}{endpoint}"
    try:
        r = session.get(url, timeout=5)
        data = r.content
        size = len(data)

        if endpoint == "/preview":
            arr = np.frombuffer(data, np.uint8)
            import cv2

            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                mean = img.mean()
                mx = img.max()
                mn = img.min()
                unique = len(np.unique(img.reshape(-1, 3), axis=0))
                print(
                    f"  [{idx}] PNG {img.shape} size={size} min={mn} max={mx} mean={mean:.1f} colors={unique} {'REAL' if unique > 10 else 'BLACK'}"
                )
                return img, unique > 10
            else:
                print(f"  [{idx}] Failed to decode PNG, size={size}")
                return None, False
        else:
            # /screenshot returns RGB565
            arr = np.frombuffer(data, dtype=np.uint16)
            total = arr.sum()
            print(f"  [{idx}] RAW size={size} sum={total} {'REAL' if total > 0 else 'BLACK'}")
            return arr, total > 0

    except Exception as e:
        print(f"  [{idx}] Error: {e}")
        return None, False


def test_stability():
    """Main test: start DroidCast and take multiple screenshots."""
    print("=== DroidCast Stability Test ===")

    print("\n1. Killing existing DroidCast...")
    kill_droidcast()

    print("\n2. Removing port forwards...")
    remove_forwards()

    print("\n3. Starting DroidCast via u2 ATX agent...")
    start_droidcast_via_u2()

    print("\n4. Setting up port forward...")
    port = setup_forward()

    print("\n5. Waiting for DroidCast startup...")
    session, port = wait_startup(port)

    print("\n6. Taking 5 consecutive /preview screenshots (0.5s apart)...")
    results = []
    for i in range(5):
        _, ok = take_screenshot(session, port, i, "/preview")
        results.append(ok)
        time.sleep(0.5)

    print(f"\n/preview results: {sum(results)}/5 real frames")

    if sum(results) < 3:
        print("\n7. Retrying with /screenshot (RGB565) endpoint...")
        for i in range(5):
            _, ok = take_screenshot(session, port, i, "/screenshot")
            time.sleep(0.5)

    # Test: restart DroidCast between each screenshot
    if sum(results) < 3:
        print("\n8. Testing restart-per-screenshot strategy...")
        for i in range(3):
            print(f"\n  --- Restart cycle {i} ---")
            kill_droidcast()
            remove_forwards()
            start_droidcast_via_u2()
            port = setup_forward()
            session, port = wait_startup(port)
            _, ok = take_screenshot(session, port, i, "/preview")
            print(f"  Result: {'REAL' if ok else 'BLACK'}")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    test_stability()
