"""Orchestrate every audit in the family as one pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from honestypipeline._paths import ensure_paths

ensure_paths()

import decaywatch  # noqa: E402
import enrichaudit  # noqa: E402
import filtergap  # noqa: E402
import linguacheck  # noqa: E402
import nuancebench  # noqa: E402
import readypack  # noqa: E402
import sourcelock  # noqa: E402
import whychanged  # noqa: E402
from decaywatch import run as run_decaywatch  # noqa: E402
from enrichaudit import run as run_enrichaudit  # noqa: E402
from filtergap import run as run_filtergap  # noqa: E402
from linguacheck import run as run_linguacheck  # noqa: E402
from nuancebench import run as run_nuancebench  # noqa: E402
from readypack import run as run_readypack  # noqa: E402
from sourcelock import run as run_sourcelock  # noqa: E402
from whychanged import run as run_whychanged  # noqa: E402

TOOL_VERSIONS = {
    "decaywatch": getattr(decaywatch, "__version__", "0.1.0"),
    "enrichaudit": getattr(enrichaudit, "__version__", "0.1.0"),
    "filtergap": getattr(filtergap, "__version__", "0.1.0"),
    "linguacheck": getattr(linguacheck, "__version__", "0.1.0"),
    "nuancebench": getattr(nuancebench, "__version__", "0.1.0"),
    "readypack": getattr(readypack, "__version__", "0.1.0"),
    "sourcelock": getattr(sourcelock, "__version__", "0.1.0"),
    "whychanged": getattr(whychanged, "__version__", "0.1.0"),
}

RUNNERS = [
    ("decaywatch", run_decaywatch),
    ("enrichaudit", run_enrichaudit),
    ("filtergap", run_filtergap),
    ("linguacheck", run_linguacheck),
    ("nuancebench", run_nuancebench),
    ("sourcelock", run_sourcelock),
    ("whychanged", run_whychanged),
]


@dataclass
class PipelineResult:
    status: str = "success"
    findings: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    tools: dict[str, dict] = field(default_factory=dict)
    readypack: dict[str, Any] = field(default_factory=dict)


def _to_envelope(tool: str, result: Any) -> dict[str, Any]:
    return {
        "tool": tool,
        "version": TOOL_VERSIONS.get(tool, "0.1.0"),
        "status": getattr(result, "status", "success"),
        "findings": list(getattr(result, "findings", []) or []),
        "warnings": list(getattr(result, "warnings", []) or []),
        "summary": dict(getattr(result, "summary", {}) or {}),
    }


def _options_for(tool: str, pipeline_options: dict[str, Any]) -> dict[str, Any]:
    opts: dict[str, Any] = {}
    # Top-level convenience keys that apply to every tool are intentionally
    # not forwarded; only explicit per-tool sections are.
    for source_key in ("tools",):
        section = pipeline_options.get(source_key)
        if isinstance(section, dict) and isinstance(section.get(tool), dict):
            opts.update(section[tool])
    if isinstance(pipeline_options.get(tool), dict):
        opts.update(pipeline_options[tool])
    return opts


def run_pipeline(rows: list[dict], options: dict[str, Any] | None = None) -> PipelineResult:
    """Run all eight audits and fold their findings into a ReadyPack pack."""
    options = options or {}
    out = PipelineResult()

    reports: list[dict] = []
    for tool, runner in RUNNERS:
        tool_opts = _options_for(tool, options)
        try:
            result = runner(rows, tool_opts)
        except Exception as exc:  # never let one audit sink the whole pipeline
            from readypack.common import ToolResult  # noqa: E402

            result = ToolResult(status="error", findings=[], warnings=[str(exc)], summary={"checked": len(rows)})
        envelope = _to_envelope(tool, result)
        out.tools[tool] = envelope
        reports.append(envelope)

    # ReadyPack aggregates the seven audit reports above.
    rp_opts: dict[str, Any] = {
        "name": options.get("name") or options.get("dataset_name") or "dataset",
        "description": options.get("description", ""),
        "reports": reports,
        "drop_ids": options.get("drop_ids") or options.get("drop_id") or [],
    }
    rp_opts.update(_options_for("readypack", options))
    # Keep reports authoritative even if a user supplied their own.
    rp_opts["reports"] = reports
    try:
        rp_result = run_readypack(rows, rp_opts)
    except Exception as exc:
        from common import ToolResult  # type: ignore  # noqa: E402

        rp_result = ToolResult(status="error", findings=[], warnings=[str(exc)], summary={"checked": len(rows)})
    rp_envelope = _to_envelope("readypack", rp_result)
    out.readypack = rp_envelope
    out.findings = rp_envelope["findings"]
    out.warnings = rp_envelope["warnings"]
    out.summary = rp_envelope["summary"]
    out.status = rp_envelope["status"]

    return out