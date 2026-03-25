import time

import pytest

from state_cartographer.transport.adb import Adb
from state_cartographer.transport.config import artifacts_dir, load_config
from state_cartographer.transport.maamcp import MaaAdapter


def test_live_maamcp_smoke():
    cfg = load_config()
    adb = Adb(cfg.serial)
    if not adb.is_device_online():
        pytest.skip("Device offline, skipping live test")

    adapter = MaaAdapter(cfg.serial, agent_path=cfg.agent_path)
    assert adapter.connect()

    # capturing frame
    out_dir = artifacts_dir()
    cap_path = out_dir / "test_live_maamcp_cap.png"
    data, _elapsed_ms = adapter.screenshot(cap_path)

    assert data is not None
    assert len(data) > 100
    assert cap_path.exists()

    # physical dispatch
    assert adapter.tap(50, 50)
    time.sleep(0.5)
    assert adapter.swipe(100, 300, 100, 500, duration_ms=200)
