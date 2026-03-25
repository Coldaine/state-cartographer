"""Transport layer for adbutils+MaaTouch emulator control.

Public surface:
    - config: load_config, TransportConfig
    - adb: Adb class (adbutils-based, no subprocess)
    - maatouch: MaaTouch precision touch controller
    - capture: Screenshot capture methods
    - models: probe result / report types
    - health: readiness checks and recovery ladder
    - artifacts: write structured results to data/events/memu-transport/
"""

from state_cartographer.transport.config import TransportConfig, load_config
from state_cartographer.transport.models import (
    BootstrapManifest,
    ControlLayerStatus,
    DoctorReport,
    MaaCaptureResult,
    MaaProbeReport,
    ObservationDecision,
    ObservationLayerStatus,
    ProbeVerdict,
    ReadinessTier,
    ScrcpyProbeReport,
    SessionProbeReport,
    ToolEntry,
    TransportLayerStatus,
)
from state_cartographer.transport.adb import Adb, AdbError
from state_cartographer.transport.maatouch import (
    MaaTouch,
    MaaTouchError,
    MaaTouchNotInstalledError,
    MaaTouchSyncTimeout,
)
from state_cartographer.transport.capture import Capture, capture_burst

__all__ = [
    "Adb",
    "AdbError",
    "BootstrapManifest",
    "Capture",
    "ControlLayerStatus",
    "DoctorReport",
    "MaaCaptureResult",
    "MaaProbeReport",
    "MaaTouch",
    "MaaTouchError",
    "MaaTouchNotInstalledError",
    "MaaTouchSyncTimeout",
    "ObservationDecision",
    "ObservationLayerStatus",
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
