import pytest

from state_cartographer.transport.adb import Adb
from state_cartographer.transport.config import load_config
from state_cartographer.transport.discovery import bootstrap
from state_cartographer.transport.health import recovery_ladder


def test_live_recovery_ladder():
    cfg = load_config()
    manifest = bootstrap(cfg)
    adb_path = next((tool.path for tool in manifest.tools if tool.name == "adb" and tool.found and tool.path), None)
    if not adb_path:
        pytest.skip("adb unavailable, skipping recovery test")

    adb = Adb(cfg.serial, adb_path=adb_path)
    if not adb.is_device_online():
        pytest.skip("Device offline, skipping recovery test")

    # Force disconnect
    adb.disconnect()

    # Observe recovery
    recovered = recovery_ladder(cfg, adb_path=adb_path)
    assert recovered, "Recovery ladder should successfully reconnect"
    assert adb.is_device_online(), "Device should be online after recovery"
