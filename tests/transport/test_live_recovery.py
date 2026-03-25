"""Live recovery tests for transport layer.

These require a running MEmu emulator.
"""

import pytest

from state_cartographer.transport.adb import Adb
from state_cartographer.transport.config import load_config
from state_cartographer.transport.health import recovery_ladder


def test_live_recovery_ladder():
    cfg = load_config()
    adb = Adb(cfg.serial)

    if not adb.is_device_online():
        pytest.skip("Device offline, skipping recovery test")

    adb.disconnect()

    recovered = recovery_ladder(cfg)
    assert recovered is True
    assert adb.is_device_online() is True
