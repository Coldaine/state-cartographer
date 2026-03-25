import time

import pytest

from state_cartographer.transport.adb import Adb
from state_cartographer.transport.config import artifacts_dir, load_config
from state_cartographer.transport.discovery import bootstrap
from state_cartographer.transport.maamcp import MaaAdapter


def test_live_control_adapter_smoke():
    cfg = load_config()
    manifest = bootstrap(cfg)
    adb_path = next((tool.path for tool in manifest.tools if tool.name == "adb" and tool.found and tool.path), None)
    if not adb_path:
        pytest.skip("adb unavailable, skipping live test")

    adb = Adb(cfg.serial, adb_path=adb_path)
    if not adb.is_device_online():
        pytest.skip("Device offline, skipping live test")

    adapter = MaaAdapter(cfg.serial, adb_path=adb_path, agent_path=cfg.agent_path)
    assert adapter.connect()

    # This is a control-adapter smoke test, not proof of the native Maa path.
    assert adapter.backend in {"adb_direct", "maafw"}

    out_dir = artifacts_dir()
    cap_path = out_dir / "test_live_control_adapter_cap.png"
    data, _elapsed_ms = adapter.screenshot(cap_path)

    assert data is not None
    assert len(data) > 100
    assert cap_path.exists()

    assert adapter.tap(50, 50)
    time.sleep(0.5)
    assert adapter.swipe(100, 300, 100, 500, duration_ms=200)
