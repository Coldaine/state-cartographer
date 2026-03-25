from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayGeometry:
    width: int
    height: int


class ADBClient:
    def __init__(self, serial: str):
        self.serial = serial

    @property
    def available(self) -> bool:
        return shutil.which("adb") is not None

    def command(self, *parts: str) -> list[str]:
        return ["adb", "-s", self.serial, *parts]

    def run(
        self, *parts: str, capture_output: bool = False, text: bool = False
    ) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            self.command(*parts),
            check=True,
            capture_output=capture_output,
            text=text,
        )

    def shell(self, *parts: str, capture_output: bool = False, text: bool = False):
        return self.run("shell", *parts, capture_output=capture_output, text=text)

    def exec_out(self, *parts: str) -> bytes:
        return self.run("exec-out", *parts, capture_output=True).stdout

    def get_display_geometry(self) -> DisplayGeometry:
        completed = self.shell("wm", "size", capture_output=True, text=True)
        text = completed.stdout or ""
        match = re.search(r"Physical size:\s*(\d+)x(\d+)", text)
        if not match:
            match = re.search(r"Override size:\s*(\d+)x(\d+)", text)
        if not match:
            raise RuntimeError(f"unable_to_parse_wm_size:{text.strip()}")
        return DisplayGeometry(width=int(match.group(1)), height=int(match.group(2)))
