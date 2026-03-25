"""Live smoke tests for transport layer.

These require a running MEmu emulator. They are skipped if the device is offline.
"""

import time

import pytest

from state_cartographer.transport.adb import Adb
from state_cartographer.transport.capture import Capture
from state_cartographer.transport.config import load_config
from state_cartographer.transport.maatouch import MaaTouch


def test_live_adb_screenshot():
    cfg = load_config()
    adb = Adb(cfg.serial)

    if not adb.is_device_online():
        pytest.skip("Device offline, skipping live test")

    data = adb.screenshot_png()
    assert data is not None
    assert len(data) > 100


def test_live_adb_tap():
    cfg = load_config()
    adb = Adb(cfg.serial)

    if not adb.is_device_online():
        pytest.skip("Device offline, skipping live test")

    ok = adb.tap(100, 100)
    assert ok is True


def test_live_adb_input_methods():
    cfg = load_config()
    adb = Adb(cfg.serial)

    if not adb.is_device_online():
        pytest.skip("Device offline, skipping live test")

    assert adb.is_device_online()
    assert adb.connect()
    assert adb.devices() is not None


def test_live_capture_screenshot():
    cfg = load_config()
    adb = Adb(cfg.serial)

    if not adb.is_device_online():
        pytest.skip("Device offline, skipping live test")

    capture = Capture(adb)
    data = capture.screenshot_png()

    assert data is not None
    assert len(data) > 100


def test_live_maatouch_tap():
    cfg = load_config()
    adb = Adb(cfg.serial)

    if not adb.is_device_online():
        pytest.skip("Device offline, skipping live test")

    maatouch = MaaTouch(adb)
    if not maatouch.connect():
        pytest.skip("MaaTouch not available, skipping test")

    try:
        ok = maatouch.tap(200, 200)
        assert ok is True
    finally:
        maatouch.disconnect()


def test_live_maatouch_swipe():
    cfg = load_config()
    adb = Adb(cfg.serial)

    if not adb.is_device_online():
        pytest.skip("Device offline, skipping live test")

    maatouch = MaaTouch(adb)
    if not maatouch.connect():
        pytest.skip("MaaTouch not available, skipping test")

    try:
        ok = maatouch.swipe(100, 300, 100, 500, duration_ms=200)
        assert ok is True
    finally:
        maatouch.disconnect()
