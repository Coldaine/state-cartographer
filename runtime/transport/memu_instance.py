from __future__ import annotations

from dataclasses import dataclass

from runtime.config.models import RuntimeConfig
from runtime.transport.adb_client import ADBClient
from runtime.transport.input_controller import InputController
from runtime.transport.scrcpy_stream import ScrcpyStream


@dataclass
class MEmuInstance:
    config: RuntimeConfig

    def __post_init__(self) -> None:
        self.adb = ADBClient(self.config.adb_serial)
        self.stream = ScrcpyStream(
            serial=self.config.adb_serial,
            executable=self.config.scrcpy_executable,
            max_fps=self.config.scrcpy_max_fps,
        )

    def input_controller(self) -> InputController:
        geometry = self.adb.get_display_geometry()
        return InputController(self.adb, geometry)
