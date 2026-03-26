"""Transport layer for adbutils+MaaTouch emulator control.

Public surface:
    - Pilot: unified facade (recommended entry point)
    - config: load_config, TransportConfig
    - adb: Adb class (adbutils-based, no subprocess)
    - maatouch: MaaTouch precision touch controller
    - capture: Screenshot capture methods
    - health: readiness checks and recovery ladder
    - models: probe result / report types
    - artifacts: write structured results to data/events/memu-transport/
"""

from state_cartographer.transport.adb import Adb, AdbError
from state_cartographer.transport.capture import Capture, capture_burst
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
    ObservationDecision,
    ObservationLayerStatus,
    ProbeVerdict,
    ReadinessTier,
    ScrcpyProbeReport,
    SessionProbeReport,
    ToolEntry,
    TransportLayerStatus,
)
from state_cartographer.transport.pilot import Pilot

__all__ = [
    "Adb",
    "AdbError",
    "Capture",
    "ControlLayerStatus",
    "DoctorReport",
    "MaaTouch",
    "MaaTouchError",
    "MaaTouchNotInstalledError",
    "MaaTouchSyncTimeout",
    "ObservationDecision",
    "ObservationLayerStatus",
    "Pilot",
    "ProbeVerdict",
    "ReadinessTier",
    "ScrcpyProbeReport",
    "SessionProbeReport",
    "ToolEntry",
    "TransportConfig",
    "TransportLayerStatus",
    "capture_burst",
    "load_config",
]
