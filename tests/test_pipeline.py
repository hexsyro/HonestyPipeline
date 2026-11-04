from pathlib import Path

from honestypipeline import run_pipeline
from readypack.common import load_rows

SAMPLE = Path(__file__).resolve().parents[1] / "repos" / "EnrichAudit" / "examples" / "sample.csv"


def test_run_pipeline_returns_envelope():
    rows = load_rows(SAMPLE)
    result = run_pipeline(rows, {"name": "demo"})
    assert result.status == "success"
    assert isinstance(result.tools, dict)
    assert "enrichaudit" in result.tools
    assert result.readypack.get("tool") == "readypack"
    assert result.summary.get("health_score", {}).get("score") is not None


def test_run_pipeline_all_tools_present():
    rows = load_rows(SAMPLE)
    result = run_pipeline(rows)
    expected = {"decaywatch", "enrichaudit", "filtergap", "linguacheck",
                "nuancebench", "sourcelock", "whychanged", "readypack"}
    assert set(result.tools) | {"readypack"} == expected