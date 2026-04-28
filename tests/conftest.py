from __future__ import annotations

import pytest

from state_cartographer.run_recording import RunRecorder


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest.fixture
def live_run_recorder(request):
    if request.node.get_closest_marker("live") is None:
        yield None
        return

    recorder = RunRecorder(
        "pytest-live-transport",
        command=[request.node.nodeid],
        write_summary=False,
    )
    recorder.start(
        input_paths={"test_nodeid": request.node.nodeid},
        notes=["live pytest evidence"],
    )
    recorder.event("live_test_started", nodeid=request.node.nodeid)
    yield recorder
    report = getattr(request.node, "rep_call", None)
    exit_code = 0 if report and report.passed else 1
    warnings = [] if exit_code == 0 else [f"live test failed: {request.node.nodeid}"]
    recorder.finish(
        exit_code=exit_code,
        summary_counts={"nodeid": request.node.nodeid},
        warnings=warnings,
    )
