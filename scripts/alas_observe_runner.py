"""Passive observation runner for ALAS.

Launches the real ALAS scheduler under an existing config, but attaches repo-side
observers so the run produces:

- a screenshot corpus
- classifier observations
- session state updates
- NDJSON execution events

This script does not patch the vendor tree on disk. It monkeypatches selected
methods in-process before starting the ALAS scheduler.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
ALAS_ROOT = REPO_ROOT / "vendor" / "AzurLaneAutoScript"
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(ALAS_ROOT))

from execution_event_log import append_event, make_event
from locate import load_json as load_graph_json, locate
from observe import build_observations, extract_pixel_coords
from session import confirm_state, init_session, record_transition, save_json


def utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def infer_target_name(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str | None:
    if "target" in kwargs and kwargs["target"] is not None:
        return str(kwargs["target"])
    if not args:
        return None
    first = args[0]
    if hasattr(first, "name"):
        return str(first.name)
    if isinstance(first, str):
        return first
    return None


def coerce_state_name(page: Any) -> str | None:
    if page is None:
        return None
    if hasattr(page, "name"):
        return str(page.name)
    return str(page)


@dataclass
class ObservationRuntime:
    graph_path: Path
    run_dir: Path

    def __post_init__(self) -> None:
        self.graph = load_graph_json(self.graph_path)
        self.pixel_coords = extract_pixel_coords(self.graph)
        self.run_id = self.run_dir.name
        self.screenshots_dir = self.run_dir / "screenshots"
        self.events_path = self.run_dir / "events.jsonl"
        self.observations_path = self.run_dir / "observations.jsonl"
        self.session_path = self.run_dir / "session.json"
        self.meta_path = self.run_dir / "meta.json"
        self.screenshot_index = 0
        self.current_assignment: str | None = None
        self.session = init_session(str(self.graph_path))

        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        save_json(self.session_path, self.session)
        self.meta_path.write_text(
            json.dumps(
                {
                    "run_id": self.run_id,
                    "graph_path": str(self.graph_path),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def _session_state(self) -> str | None:
        return self.session.get("current_state")

    def _write_observation_record(self, record: dict[str, Any]) -> None:
        with self.observations_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def _persist_session(self) -> None:
        save_json(self.session_path, self.session)

    def _graph_has_state(self, state_name: str | None) -> bool:
        return bool(state_name) and state_name in self.graph.get("states", {})

    def log_event(self, **kwargs: Any) -> None:
        event = make_event(
            run_id=self.run_id,
            serial=kwargs.pop("serial"),
            assignment=kwargs.pop("assignment", self.current_assignment),
            **kwargs,
        )
        append_event(self.events_path, event)

    def run_passively(
        self,
        *,
        event_serial: str,
        observer_name: str,
        func: Any,
        **kwargs: Any,
    ) -> Any:
        try:
            return func(**kwargs)
        except KeyboardInterrupt:
            raise
        except BaseException as exc:  # noqa: BLE001
            self.log_event(
                serial=event_serial,
                event_type="recovery",
                semantic_action="observer_error",
                primitive_action=None,
                target=observer_name,
                state_before=self._session_state(),
                ok=False,
                duration_ms=0,
                error=type(exc).__name__,
                notes=str(exc),
            )
            return None

    def record_action(
        self,
        *,
        serial: str,
        event_type: str,
        semantic_action: str,
        primitive_action: str | None,
        target: str | None,
        ok: bool,
        duration_ms: int,
        error: str | None = None,
        coords: list[int] | None = None,
    ) -> None:
        state_before = self._session_state()
        if ok and primitive_action not in {None, "screenshot"}:
            transition_id = semantic_action if not target else f"{semantic_action}:{target}"
            self.session = record_transition(self.session, transition_id)
            self._persist_session()
        self.log_event(
            serial=serial,
            event_type=event_type,
            semantic_action=semantic_action,
            primitive_action=primitive_action,
            target=target,
            coords=coords,
            state_before=state_before,
            state_after=self._session_state(),
            ok=ok,
            duration_ms=duration_ms,
            error=error,
        )

    def record_page_confirmation(
        self,
        *,
        serial: str,
        page_name: str | None,
        semantic_action: str = "ui_get_current_page",
    ) -> None:
        if not page_name:
            return
        if not self._graph_has_state(page_name):
            self.log_event(
                serial=serial,
                event_type="recovery",
                semantic_action="unmodeled_page_observed",
                primitive_action=None,
                target=page_name,
                state_before=self._session_state(),
                ok=False,
                duration_ms=0,
            )
            return
        state_before = self._session_state()
        self.session = confirm_state(self.session, page_name)
        self._persist_session()
        self.log_event(
            serial=serial,
            event_type="observation",
            semantic_action=semantic_action,
            primitive_action=None,
            target=page_name,
            state_before=state_before,
            state_after=page_name,
            ok=True,
            duration_ms=0,
        )

    def record_screenshot(self, *, serial: str, image: Any) -> None:
        from PIL import Image

        state_before = self._session_state()
        self.screenshot_index += 1
        screenshot_path = self.screenshots_dir / f"{self.screenshot_index:06d}.png"
        if isinstance(image, Image.Image):
            image_to_save = image
        else:
            image_to_save = Image.fromarray(image)
        image_to_save.save(screenshot_path)

        obs = build_observations(screenshot_path, self.pixel_coords)
        result = locate(self.graph, self.session, obs)
        matched_state = result.get("state")

        if matched_state and matched_state != "unknown":
            self.session = confirm_state(self.session, matched_state)
            self._persist_session()

        self._write_observation_record(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "assignment": self.current_assignment,
                "screenshot": str(screenshot_path),
                "locate_result": result,
                "current_state": self.session.get("current_state"),
            }
        )

        self.log_event(
            serial=serial,
            event_type="observation",
            semantic_action="screenshot_capture",
            primitive_action="screenshot",
            target=None,
            state_before=state_before,
            state_after=self.session.get("current_state"),
            screen_after=str(screenshot_path),
            ok=True,
            duration_ms=0,
        )

    def infer_coords(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> list[int] | None:
        if "x" in kwargs and "y" in kwargs:
            return [int(kwargs["x"]), int(kwargs["y"])]
        if len(args) >= 2 and all(isinstance(value, (int, float)) for value in args[:2]):
            return [int(args[0]), int(args[1])]
        if len(args) >= 4 and all(isinstance(value, (int, float)) for value in args[:4]):
            return [int(args[0]), int(args[1]), int(args[2]), int(args[3])]

        first = args[0] if args else kwargs.get("target")
        button = getattr(first, "button", None)
        if isinstance(button, (list, tuple)) and len(button) >= 4:
            return [int(button[0]), int(button[1]), int(button[2]), int(button[3])]
        return None


def patch_alas_observers(runtime: ObservationRuntime) -> None:
    from alas import AzurLaneAutoScript
    from module.device.app_control import AppControl
    from module.device.control import Control
    from module.device.screenshot import Screenshot
    from module.ui.ui import UI

    original_get_next_task = AzurLaneAutoScript.get_next_task
    original_run = AzurLaneAutoScript.run
    original_screenshot = Screenshot.screenshot
    original_ui_get_current_page = UI.ui_get_current_page

    def wrap_action(method_name: str, event_type: str, primitive_action: str | None = None) -> None:
        original = getattr(Control, method_name)
        if getattr(original, "__sc_observe_wrapped__", False):
            return

        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            import time

            started = time.perf_counter()
            ok = False
            error = None
            try:
                result = original(self, *args, **kwargs)
                ok = True
                return result
            except Exception as exc:
                error = type(exc).__name__
                raise
            finally:
                serial = str(getattr(self.config, "Emulator_Serial", "unknown"))
                runtime.record_action(
                    serial=serial,
                    event_type=event_type,
                    semantic_action=method_name,
                    primitive_action=primitive_action or method_name,
                    target=infer_target_name(args, kwargs),
                    ok=ok,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    error=error,
                    coords=runtime.infer_coords(args, kwargs),
                )

        wrapper.__sc_observe_wrapped__ = True
        setattr(Control, method_name, wrapper)

    def wrap_app_action(method_name: str) -> None:
        original = getattr(AppControl, method_name)
        if getattr(original, "__sc_observe_wrapped__", False):
            return

        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            import time

            started = time.perf_counter()
            ok = False
            error = None
            try:
                result = original(self, *args, **kwargs)
                ok = True
                return result
            except Exception as exc:
                error = type(exc).__name__
                raise
            finally:
                serial = str(getattr(self.config, "Emulator_Serial", "unknown"))
                runtime.record_action(
                    serial=serial,
                    event_type="execution",
                    semantic_action=method_name,
                    primitive_action=method_name,
                    target=None,
                    ok=ok,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    error=error,
                )

        wrapper.__sc_observe_wrapped__ = True
        setattr(AppControl, method_name, wrapper)

    def screenshot_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        image = original_screenshot(self, *args, **kwargs)
        serial = str(getattr(self.config, "Emulator_Serial", "unknown"))
        runtime.run_passively(
            event_serial=serial,
            observer_name="record_screenshot",
            func=runtime.record_screenshot,
            serial=serial,
            image=image,
        )
        return image

    def ui_get_current_page_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        page = original_ui_get_current_page(self, *args, **kwargs)
        serial = str(getattr(self.config, "Emulator_Serial", "unknown"))
        runtime.run_passively(
            event_serial=serial,
            observer_name="record_page_confirmation",
            func=runtime.record_page_confirmation,
            serial=serial,
            page_name=coerce_state_name(page),
        )
        return page

    def get_next_task_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        task = original_get_next_task(self, *args, **kwargs)
        runtime.current_assignment = str(task)
        return task

    def run_wrapper(self: Any, command: str, skip_first_screenshot: bool = False) -> Any:
        import time

        started = time.perf_counter()
        serial = str(getattr(self.config, "Emulator_Serial", "unknown"))
        assignment = runtime.current_assignment or command
        runtime.log_event(
            serial=serial,
            assignment=assignment,
            event_type="assignment",
            semantic_action="assignment_start",
            primitive_action=None,
            target=command,
            state_before=runtime.session.get("current_state"),
            ok=True,
            duration_ms=0,
        )
        ok = False
        error = None
        try:
            result = original_run(self, command, skip_first_screenshot=skip_first_screenshot)
            ok = bool(result)
            return result
        except Exception as exc:
            error = type(exc).__name__
            raise
        finally:
            runtime.log_event(
                serial=serial,
                assignment=assignment,
                event_type="assignment",
                semantic_action="assignment_end",
                primitive_action=None,
                target=command,
                state_before=runtime.session.get("current_state"),
                ok=ok,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error=error,
            )

    Screenshot.screenshot = screenshot_wrapper
    UI.ui_get_current_page = ui_get_current_page_wrapper
    AzurLaneAutoScript.get_next_task = get_next_task_wrapper
    AzurLaneAutoScript.run = run_wrapper

    for name in ["click", "multi_click", "long_click", "swipe", "swipe_vector", "drag"]:
        wrap_action(name, event_type="execution")

    for name in ["app_start", "app_stop", "dump_hierarchy"]:
        wrap_app_action(name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ALAS with passive repo-side observers")
    parser.add_argument("--config", default="PatrickCustom", help="ALAS config name (default: PatrickCustom)")
    parser.add_argument(
        "--graph",
        default=str(REPO_ROOT / "examples/azur-lane/graph.json"),
        help="Path to graph.json for classification",
    )
    parser.add_argument(
        "--run-dir",
        help="Directory to write observation artifacts. Defaults to data/alas-observe/<run_id>",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    graph_path = Path(args.graph).resolve()
    run_dir = (
        Path(args.run_dir).resolve()
        if args.run_dir
        else (REPO_ROOT / "data" / "alas-observe" / f"{utc_now_compact()}-{args.config}").resolve()
    )

    os.chdir(ALAS_ROOT)

    runtime = ObservationRuntime(graph_path=graph_path, run_dir=run_dir)
    patch_alas_observers(runtime)

    from alas import AzurLaneAutoScript

    alas = AzurLaneAutoScript(args.config)
    alas.loop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
