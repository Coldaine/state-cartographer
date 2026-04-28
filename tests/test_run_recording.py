from __future__ import annotations

import json

from state_cartographer.run_recording import RunRecorder


def test_run_recorder_manifest_lifecycle(tmp_path, monkeypatch):
    runs_root = tmp_path / "runs"
    summary_root = tmp_path / "summaries"
    config_path = tmp_path / "config.json"
    config_path.write_text('{"adb_serial":"127.0.0.1:21503"}\n', encoding="utf-8")

    monkeypatch.setenv("SC_RUN_DATA_ROOT", str(runs_root))
    monkeypatch.setenv("SC_RUN_SUMMARY_ROOT", str(summary_root))

    recorder = RunRecorder("unit-lane", command=["tool", "subcommand"])
    run_id = recorder.start(
        run_id="unit-run",
        config_path=config_path,
        serial="127.0.0.1:21503",
        model="local-model",
        base_url="http://localhost:18900/v1",
        input_paths={"config": config_path},
        notes=["unit test"],
    )
    assert run_id == "unit-run"

    payload_path = recorder.artifact_path("payload.json")
    payload_path.write_text('{"ok": true}\n', encoding="utf-8")
    recorder.event("phase_completed", phase="unit", output=str(payload_path))
    manifest = recorder.finish(
        exit_code=0,
        output_paths={"payload": payload_path},
        summary_counts={"rows": 3},
    )

    manifest_data = json.loads((runs_root / "unit-run" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_data["run_id"] == "unit-run"
    assert manifest_data["status"] == "succeeded"
    assert manifest_data["serial"] == "127.0.0.1:21503"
    assert manifest_data["summary_counts"]["rows"] == 3
    assert manifest_data["output_paths"]["payload"].endswith("payload.json")

    event_lines = (runs_root / "unit-run" / "events.ndjson").read_text(encoding="utf-8").strip().splitlines()
    assert len(event_lines) >= 2
    first_event = json.loads(event_lines[0])
    assert first_event["kind"] == "run_started"

    summary_files = list(summary_root.glob("*.md"))
    assert len(summary_files) == 1
    summary_text = summary_files[0].read_text(encoding="utf-8")
    assert "Run Summary: unit-lane" in summary_text
    assert "`rows`: `3`" in summary_text
    assert manifest.summary_path is not None
