from __future__ import annotations

from urllib.parse import quote_plus

from runtime.transport.adb_client import ADBClient, DisplayGeometry


class InputController:
    def __init__(self, adb: ADBClient, geometry: DisplayGeometry):
        self.adb = adb
        self.geometry = geometry

    def normalized_to_pixels(self, x: float, y: float) -> tuple[int, int]:
        px = max(0, min(self.geometry.width - 1, round(x * self.geometry.width)))
        py = max(0, min(self.geometry.height - 1, round(y * self.geometry.height)))
        return px, py

    def pixels_to_normalized(self, x: int, y: int) -> tuple[float, float]:
        return (
            max(0.0, min(1.0, x / max(1, self.geometry.width))),
            max(0.0, min(1.0, y / max(1, self.geometry.height))),
        )

    def tap(self, x: float, y: float) -> tuple[int, int]:
        px, py = self.normalized_to_pixels(x, y)
        self.adb.shell("input", "tap", str(px), str(py))
        return px, py

    def swipe(self, x1: float, y1: float, x2: float, y2: float, duration_ms: int = 250) -> tuple[int, int, int, int]:
        px1, py1 = self.normalized_to_pixels(x1, y1)
        px2, py2 = self.normalized_to_pixels(x2, y2)
        self.adb.shell("input", "swipe", str(px1), str(py1), str(px2), str(py2), str(duration_ms))
        return px1, py1, px2, py2

    def key(self, keycode: str) -> None:
        self.adb.shell("input", "keyevent", keycode)

    def text(self, value: str) -> None:
        self.adb.shell("input", "text", quote_plus(value))
