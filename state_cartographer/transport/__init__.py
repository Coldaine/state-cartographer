"""Transport layer for adbutils+MaaTouch emulator control.

Public surface:
    - Pilot: unified facade (recommended entry point)
    - config: load_config, TransportConfig
    - adb: Adb class (adbutils-based, no subprocess)
    - maatouch: MaaTouch precision touch controller
    - health: readiness checks and recovery ladder
    - models: probe result / report types
    - artifacts: write structured results to data/events/memu-transport/
"""

from state_cartographer.transport.adb import Adb, AdbError
from state_cartographer.transport.config import TransportConfig, load_config
from state_cartographer.transport.maatouch import (
    MaaTouch,
    MaaTouchError,
    MaaTouchNotInstalledError,
    MaaTouchSyncTimeout,
)
from state_cartographer.transport.models import (
    ControlLayerStatus,
    DoctorReport,
    ObservationLayerStatus,
    ProbeVerdict,
    ReadinessTier,
    SessionProbeReport,
    ToolEntry,
    TransportLayerStatus,
)
from state_cartographer.transport.pilot import Pilot

__all__ = [
    "Adb",
    "AdbError",
    "ControlLayerStatus",
    "DoctorReport",
    "MaaTouch",
    "MaaTouchError",
    "MaaTouchNotInstalledError",
    "MaaTouchSyncTimeout",
    "ObservationLayerStatus",
    "Pilot",
    "ProbeVerdict",
    "ReadinessTier",
    "SessionProbeReport",
    "ToolEntry",
    "TransportConfig",
    "TransportLayerStatus",
    "load_config",
]
