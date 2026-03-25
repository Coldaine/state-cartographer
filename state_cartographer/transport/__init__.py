"""Transport layer for borrowed-substrate emulator attachment.

Public surface:
    - config: load_config, TransportConfig
    - models: probe result / report types
    - discovery: bootstrap and discover external tools
    - maamcp: MaaMCP adapter (connect, screenshot, input)
    - scrcpy_probe: scrcpy coexistence verification
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

__all__ = [
    "BootstrapManifest",
    "ControlLayerStatus",
    "DoctorReport",
    "MaaCaptureResult",
    "MaaProbeReport",
    "ObservationDecision",
    "ObservationLayerStatus",
    "ProbeVerdict",
    "ReadinessTier",
    "ScrcpyProbeReport",
    "SessionProbeReport",
    "ToolEntry",
    "TransportConfig",
    "TransportLayerStatus",
    "load_config",
]
