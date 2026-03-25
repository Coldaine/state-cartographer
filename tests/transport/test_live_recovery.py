import pytest

from state_cartographer.transport.adb import Adb
from state_cartographer.transport.config import load_config
from state_cartographer.transport.health import recovery_ladder


def test_live_recovery_ladder():
    cfg = load_config()
    adb = Adb(cfg.serial)
    if not adb.is_device_online():
        pytest.skip("Device offline, skipping recovery test")

    # Force disconnect
    adb.disconnect()

    # Observe recovery
    recovered = recovery_ladder(cfg)
    assert recovered, "Recovery ladder should successfully reconnect"
    assert adb.is_device_online(), "Device should be online after recovery"
