"""MaaTouch protocol for precision touch input.

Uses adbutils shell stream transport. Faster and more precise than
adb shell input. Protocol: banner on stdout, minitouch commands to stream,
timestamp echo-back for sync mode.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from state_cartographer.transport.adb import Adb

log = logging.getLogger(__name__)

DEFAULT_REMOTE_PATH = "/data/local/tmp/maatouchsync"
DEFAULT_LOCAL_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "ALAS_original" / "bin" / "MaaTouch" / "maatouchsync"
)


@dataclass
class Command:
    operation: str
    contact: int = 0
    x: int = 0
    y: int = 0
    ms: int = 10
    pressure: int = 100
    mode: int = 0
    text: str = ""

    def to_minitouch(self) -> str:
        if self.operation == "c" or self.operation == "r":
            return f"{self.operation}\n"
        elif self.operation == "d" or self.operation == "m":
            return f"{self.operation} {self.contact} {self.x} {self.y} {self.pressure}\n"
        elif self.operation == "u":
            return f"{self.operation} {self.contact}\n"
        elif self.operation == "w":
            return f"{self.operation} {self.ms}\n"
        else:
            return ""

    def to_maatouch_sync(self) -> str:
        if self.operation == "c":
            return f"{self.operation}\n"
        elif self.operation == "r":
            if self.mode:
                return f"{self.operation} {self.mode}\n"
            return f"{self.operation}\n"
        elif self.operation == "d" or self.operation == "m":
            if self.mode:
                return f"{self.operation} {self.contact} {self.x} {self.y} {self.pressure} {self.mode}\n"
            return f"{self.operation} {self.contact} {self.x} {self.y} {self.pressure}\n"
        elif self.operation == "u":
            if self.mode:
                return f"{self.operation} {self.contact} {self.mode}\n"
            return f"{self.operation} {self.contact}\n"
        elif self.operation == "w":
            return f"{self.operation} {self.ms}\n"
        elif self.operation == "s":
            return f"{self.operation} {self.text}\n"
        else:
            return ""


class CommandBuilder:
    DEFAULT_DELAY = 0.05

    def __init__(self, device: MaaTouch, contact: int = 0):
        self.device = device
        self.contact = contact
        self.commands: list[Command] = []
        self.delay = 0

    def commit(self) -> CommandBuilder:
        self.commands.append(Command("c"))
        return self

    def reset(self, mode: int = 0) -> CommandBuilder:
        self.commands.append(Command("r", mode=mode))
        return self

    def wait(self, ms: int = 10) -> CommandBuilder:
        self.commands.append(Command("w", ms=ms))
        self.delay += ms
        return self

    def up(self, mode: int = 0) -> CommandBuilder:
        self.commands.append(Command("u", contact=self.contact, mode=mode))
        return self

    def down(self, x: int, y: int, pressure: int = 100, mode: int = 0) -> CommandBuilder:
        self.commands.append(Command("d", x=x, y=y, contact=self.contact, pressure=pressure, mode=mode))
        return self

    def move(self, x: int, y: int, pressure: int = 100, mode: int = 0) -> CommandBuilder:
        self.commands.append(Command("m", x=x, y=y, contact=self.contact, pressure=pressure, mode=mode))
        return self

    def clear(self) -> CommandBuilder:
        self.commands = []
        self.delay = 0
        return self

    def to_minitouch(self) -> str:
        return "".join(cmd.to_minitouch() for cmd in self.commands)

    def to_maatouch_sync(self) -> str:
        return "".join(cmd.to_maatouch_sync() for cmd in self.commands)


class MaaTouchError(Exception):
    pass


class MaaTouchNotInstalledError(MaaTouchError):
    pass


class MaaTouchSyncTimeout(MaaTouchError):
    pass


class MaaTouch:
    """MaaTouch precision touch controller.

    Communicates via adbutils shell stream.
    maatouchsync reads minitouch commands from stream writes and echoes
    timestamps back on stream reads for sync-mode confirmation.
    """

    def __init__(
        self,
        adb: Adb,
        local_path: Path = DEFAULT_LOCAL_PATH,
        remote_path: str = DEFAULT_REMOTE_PATH,
    ):
        self.adb = adb
        self.local_path = local_path
        self.remote_path = remote_path
        self._conn = None
        self._stdout_q: queue.Queue = queue.Queue()
        self._reader_thread: threading.Thread | None = None
        self._max_x = 1280
        self._max_y = 720
        self._installed = False

    def _ensure_installed(self) -> bool:
        if self._installed:
            return True
        if not self.local_path.exists():
            log.error(f"MaaTouch binary not found at {self.local_path}")
            return False
        result = self.adb.push(self.local_path, self.remote_path)
        if result:
            self.adb.shell(["chmod", "755", self.remote_path])
            self._installed = True
            log.info(f"MaaTouch installed to {self.remote_path}")
        return result

    def _start_reader(self) -> None:
        """Background thread that drains stream output lines into a queue."""

        def _reader():
            if self._conn is None:
                return
            buffer = b""
            try:
                while True:
                    chunk = self._conn.read(1024)
                    if not chunk:
                        break
                    buffer += chunk
                    while b"\n" in buffer:
                        raw, buffer = buffer.split(b"\n", 1)
                        self._stdout_q.put(raw.rstrip(b"\r").decode(errors="replace"))
                if buffer:
                    self._stdout_q.put(buffer.rstrip(b"\r").decode(errors="replace"))
            except Exception as e:
                log.debug("MaaTouch stream reader exited: %s", e)

        self._reader_thread = threading.Thread(target=_reader, daemon=True)
        self._reader_thread.start()

    def _readline(self, timeout: float = 3.0) -> str:
        """Read one line from stdout queue with a timeout."""
        try:
            return self._stdout_q.get(timeout=timeout)
        except queue.Empty as e:
            raise MaaTouchSyncTimeout(f"No response within {timeout}s") from e

    def connect(self) -> bool:
        if not self._ensure_installed():
            return False

        try:
            self._conn = self.adb.device.open_shell(
                f"CLASSPATH={self.remote_path} app_process / com.shxyke.MaaTouch.App"
            )
            self._start_reader()

            # Read banner: '^ <contacts> <max_x> <max_y> <max_pressure>'
            banner = self._readline(timeout=10.0)
            log.info(f"MaaTouch banner: {banner}")

            if "Aborted" in banner:
                self.disconnect()
                raise MaaTouchNotInstalledError("MaaTouch aborted — incompatible with device")

            try:
                # Strip leading '^ ' if present, or handle raw split
                parts = banner.strip().split()
                if parts[0] == "^":
                    parts = parts[1:]

                _max_contacts, max_x, max_y, _max_pressure = parts[:4]
                self._max_x = int(max_x)
                self._max_y = int(max_y)
            except (ValueError, IndexError):
                log.warning(f"Unexpected MaaTouch banner format: {banner!r}")

            # Read second banner line: '$ <max_pressure>'
            try:
                second = self._readline(timeout=1.0)
                log.debug(f"MaaTouch: {second}")
            except MaaTouchSyncTimeout:
                pass  # second line optional

            log.info(f"MaaTouch connected, max_x={self._max_x}, max_y={self._max_y}")
            return True

        except MaaTouchNotInstalledError:
            raise
        except Exception as e:
            log.error(f"MaaTouch connect failed: {e}")
            self.disconnect()
            return False

    def disconnect(self) -> None:
        if self._conn:
            with suppress(Exception):
                self._conn.close()
            self._conn = None
        self._reader_thread = None

    def is_connected(self) -> bool:
        return self._conn is not None

    def _send(self, builder: CommandBuilder) -> bool:
        """Send commands; no sync confirmation."""
        if self._conn is None:
            raise MaaTouchError("MaaTouch not connected")

        content = builder.to_minitouch().encode("utf-8")
        self._conn.send(content)
        time.sleep(builder.DEFAULT_DELAY)
        builder.clear()
        return True

    def _send_sync(self, builder: CommandBuilder, mode: int = 2) -> bool:
        """Send commands with timestamp echo-back confirmation."""
        if self._conn is None:
            raise MaaTouchError("MaaTouch not connected")

        for cmd in builder.commands[::-1]:
            if cmd.operation in ["r", "d", "m", "u"]:
                cmd.mode = mode
                break

        timestamp = str(int(time.time() * 1000))
        builder.commands.insert(0, Command("s", text=timestamp))

        content = builder.to_maatouch_sync().encode("utf-8")
        self._conn.send(content)

        # Wait for timestamp echo-back
        matched = False
        for _ in range(5):
            out = self._readline(timeout=2.0)
            if out == timestamp:
                matched = True
                break
            if out == "Killed":
                raise MaaTouchNotInstalledError("MaaTouch died")

        if not matched:
            raise MaaTouchSyncTimeout("MaaTouch sync echo not observed")

        time.sleep(builder.DEFAULT_DELAY)
        builder.clear()
        return True

    def tap(self, x: int, y: int) -> bool:
        builder = CommandBuilder(self)
        builder.down(x, y).commit()
        builder.up().commit()
        return self._send_sync(builder)

    def long_tap(self, x: int, y: int, duration_ms: int = 1000) -> bool:
        builder = CommandBuilder(self)
        builder.down(x, y).wait(duration_ms).commit()
        builder.up().commit()
        return self._send_sync(builder)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        steps = max(duration_ms // 10, 5)
        builder = CommandBuilder(self)

        builder.down(x1, y1).commit().wait(10)
        self._send_sync(builder)

        dx = (x2 - x1) / steps
        dy = (y2 - y1) / steps

        for i in range(1, steps + 1):
            builder.move(int(x1 + dx * i), int(y1 + dy * i)).wait(10)
        builder.commit()
        self._send_sync(builder)

        builder.up().commit()
        return self._send_sync(builder)

    def __enter__(self) -> MaaTouch:
        self.connect()
        return self

    def __exit__(self, *args) -> None:
        self.disconnect()
