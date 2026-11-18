import json
from pathlib import Path

from honestypipeline import cli

SAMPLE = Path(__file__).resolve().parents[1] / "repos" / "EnrichAudit" / "examples" / "sample.csv"


def test_list_tools(capsys):
    assert cli.main(["--list-tools"]) == 0
    out = capsys.readouterr().out
    assert "enrichaudit" in out and "readypack" in out
    assert "version" in out


def test_json_output_has_run_manifest(capsys):
    code = cli.main([str(SAMPLE), "--format", "json", "--quiet"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schemaVersion"] == "1.1"
    assert payload["run"]["tool"] == "honestypipeline"
    assert payload["run"]["input"]["rows"] > 0
    assert "enrichaudit" in payload["run"]["tools"]
    assert isinstance(payload["findings"], list)


def test_out_writes_run_json_and_keeps_stdout_json(tmp_path, capsys):
    out = tmp_path / "pack"
    code = cli.main([str(SAMPLE), "--format", "json", "--out", str(out), "--quiet"])
    assert code == 0
    captured = capsys.readouterr()
    json.loads(captured.out)
    assert "package written" in captured.err
    manifest = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "1.1"
    assert (out / "package.zip").is_file()


def test_only_option_limits_tools(capsys):
    code = cli.main([str(SAMPLE), "--format", "json", "--only", "enrichaudit", "--quiet"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert set(payload["run"]["tools"]) == {"enrichaudit", "readypack"}


def test_invalid_tool_name_is_usage_error(capsys):
    assert cli.main([str(SAMPLE), "--only", "nope", "--quiet"]) == 2
    assert "unknown tool" in capsys.readouterr().err


def test_fail_on_returns_one(capsys):
    code = cli.main([str(SAMPLE), "--fail-on", "low", "--quiet"])
    assert code in (0, 1)
    capsys.readouterr()


def test_tool_error_returns_three(monkeypatch, capsys):
    import honestypipeline.pipeline as pipeline

    def broken(_rows, _opts):
        raise RuntimeError("boom")

    monkeypatch.setattr(pipeline, "run_filtergap", broken)
    code = cli.main([str(SAMPLE), "--only", "filtergap", "--format", "json", "--quiet"])
    assert code == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["run"]["tools"]["filtergap"]["status"] == "error"


def test_baseline_regression_gate(tmp_path, capsys):
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"summary": {"health_score": {"score": 100}}, "findings": []}), encoding="utf-8")
    code = cli.main(
        [str(SAMPLE), "--baseline", str(baseline), "--fail-on-regression", "--quiet"],
    )
    assert code == 1
    assert "baseline score" in capsys.readouterr().err


def test_version(capsys):
    try:
        cli.main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    assert "0.2.0" in capsys.readouterr().out
