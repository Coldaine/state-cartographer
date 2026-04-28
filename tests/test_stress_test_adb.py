from __future__ import annotations

import json

from scripts import stress_test_adb as stress


def test_stress_test_compare_writes_run_artifacts(tmp_path, monkeypatch, capsys):
    image_path = tmp_path / "frame.png"
    image_path.write_bytes(b"fake")

    monkeypatch.setattr(stress, "is_black_frame", lambda data: False)
    monkeypatch.setattr(stress, "is_corrupted", lambda data: False)
    monkeypatch.setenv("SC_RUN_DATA_ROOT", str(tmp_path / "runs"))
    monkeypatch.setenv("SC_RUN_SUMMARY_ROOT", str(tmp_path / "summaries"))

    exit_code = stress.main(["--run-id", "stress-run", "--compare", str(image_path)])
    assert exit_code == 0

    manifest = json.loads((tmp_path / "runs" / "stress-run" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "succeeded"
    assert manifest["summary_counts"]["compared_paths"] == 1
    assert (tmp_path / "runs" / "stress-run" / "events.ndjson").exists()
    assert list((tmp_path / "summaries").glob("*.md"))

    captured = capsys.readouterr()
    assert "black=False" in captured.out
