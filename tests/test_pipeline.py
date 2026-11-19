from pathlib import Path

import pytest

from honestypipeline import RESULT_SCHEMA_VERSION, run_pipeline
from readypack.common import ToolResult, load_rows

SAMPLE = Path(__file__).resolve().parents[1] / "repos" / "EnrichAudit" / "examples" / "sample.csv"


def _rows():
    return load_rows(SAMPLE)


def test_run_pipeline_returns_envelope():
    rows = _rows()
    result = run_pipeline(rows, {"name": "demo"})
    assert result.status == "success"
    assert isinstance(result.tools, dict)
    assert "enrichaudit" in result.tools
    assert result.readypack.get("tool") == "readypack"
    assert result.summary.get("health_score", {}).get("score") is not None


def test_run_pipeline_all_tools_present():
    rows = _rows()
    result = run_pipeline(rows)
    expected = {
        "decaywatch",
        "enrichaudit",
        "filtergap",
        "linguacheck",
        "nuancebench",
        "sourcelock",
        "whychanged",
        "readypack",
    }
    assert set(result.tools) | {"readypack"} == expected


def test_v02_provenance_fields():
    result = run_pipeline(_rows(), {"name": "demo"})
    assert result.schema_version == RESULT_SCHEMA_VERSION == "1.1"
    assert result.run_id
    assert result.started_at and result.finished_at
    assert result.duration_ms >= 0
    assert len(result.input_fingerprint) == 64
    assert set(result.tool_runs) >= {"decaywatch", "enrichaudit", "readypack"}
    assert all("duration_ms" in run for run in result.tool_runs.values())
    assert result.summary["run_id"] == result.run_id
    assert result.summary["result_schema_version"] == "1.1"
    for envelope in result.tools.values():
        assert envelope["summary"]["result_schema_version"] == "1.1"
        assert "skipped" in envelope["summary"]


def test_only_and_skip_selection():
    only = run_pipeline(_rows(), {"only": "enrichaudit,filtergap"})
    assert set(only.tools) == {"enrichaudit", "filtergap"}
    skipped = run_pipeline(_rows(), {"skip": "decaywatch,nuancebench"})
    assert "decaywatch" not in skipped.tools
    assert "nuancebench" not in skipped.tools
    assert "enrichaudit" in skipped.tools
    with pytest.raises(ValueError, match="unknown tool"):
        run_pipeline(_rows(), {"only": "not-a-tool"})


def test_tool_runs_use_cache(tmp_path):
    options = {"cache_dir": str(tmp_path)}
    first = run_pipeline(_rows(), options)
    names = [name for name in first.tool_runs if name != "readypack"]
    assert all(not first.tool_runs[name]["cache_hit"] for name in names)
    second = run_pipeline(_rows(), options)
    assert all(second.tool_runs[name]["cache_hit"] for name in names)


def test_corroboration_tags_findings(monkeypatch):
    import honestypipeline.pipeline as pipeline

    def finding_tool(_rows, _opts):
        return ToolResult(
            status="success",
            findings=[{"severity": "low", "field": "engagement_rate", "record_id": "r1", "message": "x"}],
            warnings=[],
            summary={"checked": 1},
        )

    monkeypatch.setattr(pipeline, "run_decaywatch", finding_tool)
    monkeypatch.setattr(pipeline, "run_enrichaudit", finding_tool)
    result = run_pipeline(_rows(), {"only": "decaywatch,enrichaudit"})
    assert result.corroborated_count == 1
    tools = {env["tool"]: env for env in result.tools.values()}
    for name in ("decaywatch", "enrichaudit"):
        meta = tools[name]["findings"][0]["metadata"]["corroboration"]
        assert meta["count"] == 2
        assert set(meta["tools"]) == {"decaywatch", "enrichaudit"}


def test_tool_error_is_captured(monkeypatch):
    import honestypipeline.pipeline as pipeline

    def broken(_rows, _opts):
        raise RuntimeError("boom")

    monkeypatch.setattr(pipeline, "run_filtergap", broken)
    result = run_pipeline(_rows(), {"only": "filtergap"})
    assert result.tools["filtergap"]["status"] == "error"
    assert "boom" in result.tools["filtergap"]["warnings"][0]
