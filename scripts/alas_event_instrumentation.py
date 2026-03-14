"""Helpers to instrument ALAS methods and emit execution events."""

from __future__ import annotations

import functools
import time
from pathlib import Path
from typing import Any

from execution_event_log import append_event, make_event


def _safe_attr(obj: Any, name: str, default: Any = None) -> Any:
    try:
        return getattr(obj, name, default)
    except Exception:
        return default


def _coerce_target(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str | None:
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


def _serial_from_instance(instance: Any) -> str:
    config = _safe_attr(instance, "config")
    return _safe_attr(config, "Emulator_Serial", "unknown")


def _assignment_from_instance(instance: Any) -> str | None:
    config = _safe_attr(instance, "config")
    task = _safe_attr(config, "task")
    if task:
        return str(task)
    return None


def instrument_method(
    cls: type,
    method_name: str,
    *,
    log_path: Path,
    run_id: str,
    event_type: str,
    semantic_action: str | None = None,
    primitive_action: str | None = None,
) -> None:
    """Wrap one class method so each call emits one execution event."""
    original = getattr(cls, method_name)
    if getattr(original, "__sc_instrumented__", False):
        return

    @functools.wraps(original)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        ok = False
        error: str | None = None
        try:
            result = original(self, *args, **kwargs)
            ok = True
            return result
        except Exception as exc:
            error = type(exc).__name__
            raise
        finally:
            event = make_event(
                run_id=run_id,
                serial=_serial_from_instance(self),
                event_type=event_type,
                ok=ok,
                assignment=_assignment_from_instance(self),
                semantic_action=semantic_action or method_name,
                primitive_action=primitive_action,
                target=_coerce_target(args, kwargs),
                duration_ms=int((time.perf_counter() - started) * 1000),
                error=error,
            )
            append_event(log_path, event)

    wrapper.__sc_instrumented__ = True
    setattr(cls, method_name, wrapper)


def instrument_methods(
    cls: type,
    method_names: list[str],
    *,
    log_path: Path,
    run_id: str,
    event_type: str,
    primitive_action: str | None = None,
) -> None:
    for method_name in method_names:
        instrument_method(
            cls,
            method_name,
            log_path=log_path,
            run_id=run_id,
            event_type=event_type,
            semantic_action=method_name,
            primitive_action=primitive_action,
        )
