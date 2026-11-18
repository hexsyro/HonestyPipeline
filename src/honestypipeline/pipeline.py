"""Orchestrate every audit in the family as one pipeline."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Callable

from honestypipeline._paths import ensure_paths
from honestypipeline.manifest import (
    RESULT_SCHEMA_VERSION,
    cache_key,
    fingerprint_rows,
    read_cache,
    utc_now,
    write_cache,
)

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

TOOL_NAMES = [name for name, _ in RUNNERS] + ["readypack"]
Progress = Callable[[str, str], None]


@dataclass
class PipelineResult:
    status: str = "success"
    findings: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    tools: dict[str, dict] = field(default_factory=dict)
    readypack: dict[str, Any] = field(default_factory=dict)
    schema_version: str = RESULT_SCHEMA_VERSION
    run_id: str = ""
    started_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0
    input_fingerprint: str = ""
    tool_runs: dict[str, dict] = field(default_factory=dict)
    corroborated_count: int = 0


def _to_envelope(tool: str, result: Any) -> dict[str, Any]:
    summary = dict(getattr(result, "summary", {}) or {})
    summary.setdefault("result_schema_version", RESULT_SCHEMA_VERSION)
    summary.setdefault("skipped", False)
    summary.setdefault("skip_reason", None)
    return {
        "tool": tool,
        "version": TOOL_VERSIONS.get(tool, "0.2.0"),
        "status": getattr(result, "status", "success"),
        "findings": list(getattr(result, "findings", []) or []),
        "warnings": list(getattr(result, "warnings", []) or []),
        "summary": summary,
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
    opts.pop("enabled", None)
    return opts


def _name_list(value: Any, label: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [part.strip() for part in value.split(",") if part.strip()]
    elif isinstance(value, (list, tuple, set)):
        items = [str(part).strip() for part in value if str(part).strip()]
    else:
        raise ValueError(f"{label} must be a comma-separated string or a list of tool names")
    unknown = [item for item in items if item not in TOOL_NAMES]
    if unknown:
        raise ValueError(f"unknown tool name(s) for {label}: {', '.join(unknown)}. Valid: {', '.join(TOOL_NAMES)}")
    return items


def _tool_enabled(tool: str, options: dict[str, Any]) -> bool:
    for section in (options.get("tools"),):
        if isinstance(section, dict) and isinstance(section.get(tool), dict):
            if section[tool].get("enabled") is False:
                return False
    if isinstance(options.get(tool), dict) and options[tool].get("enabled") is False:
        return False
    return True


def _notify(progress: Progress | None, tool: str, state: str) -> None:
    if progress is None:
        return
    try:
        progress(tool, state)
    except Exception:  # progress reporting must never sink a run
        pass


def _corroborate(envelopes: list[dict[str, Any]]) -> int:
    """Tag findings corroborated by more than one audit with the same record/field."""
    groups: dict[tuple[str, str], list[tuple[str, dict[str, Any]]]] = {}
    for envelope in envelopes:
        for finding in envelope.get("findings", []):
            if not isinstance(finding, dict):
                continue
            key = (str(finding.get("record_id") or ""), str(finding.get("field") or ""))
            groups.setdefault(key, []).append((str(envelope.get("tool", "")), finding))

    corroborated = 0
    for entries in groups.values():
        tools = sorted({tool for tool, _ in entries if tool})
        if len(tools) < 2:
            continue
        corroborated += 1
        for _, finding in entries:
            metadata = finding.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
                finding["metadata"] = metadata
            metadata["corroboration"] = {"tools": tools, "count": len(tools), "status": "corroborated"}
    return corroborated


def run_pipeline(
    rows: list[dict],
    options: dict[str, Any] | None = None,
    *,
    progress: Progress | None = None,
    input_sha256: str | None = None,
) -> PipelineResult:
    """Run the selected audits and fold their findings into a ReadyPack pack."""
    options = options or {}
    rows = list(rows)
    out = PipelineResult(
        run_id=str(options.get("run_id") or uuid.uuid4()),
        started_at=utc_now(),
        input_fingerprint=input_sha256 or fingerprint_rows(rows),
    )
    started = perf_counter()

    only = _name_list(options.get("only"), "only")
    skip = _name_list(options.get("skip"), "skip")
    selected = [
        name
        for name, _ in RUNNERS
        if (not only or name in only) and name not in skip and _tool_enabled(name, options)
    ]
    cache_dir = options.get("cache_dir")
    use_cache = bool(cache_dir) and not options.get("no_cache")

    reports: list[dict] = []
    for tool in selected:
        _notify(progress, tool, "start")
        runner = globals().get(f"run_{tool}")
        if runner is None:
            runner = dict(RUNNERS)[tool]
        tool_opts = _options_for(tool, options)
        started_tool = perf_counter()
        cache_hit = False
        key = cache_key(
            fingerprint=out.input_fingerprint,
            tool=tool,
            version=TOOL_VERSIONS.get(tool, "0.2.0"),
            options=tool_opts,
        )
        if use_cache:
            cached = read_cache(cache_dir, key)  # type: ignore[arg-type]
            if cached is not None:
                envelope = cached
                cache_hit = True
        if not cache_hit:
            try:
                result = runner(rows, tool_opts)
                state = "done"
            except Exception as exc:  # never let one audit sink the whole pipeline
                from readypack.common import ToolResult  # noqa: E402

                result = ToolResult(
                    status="error",
                    findings=[],
                    warnings=[f"{tool}: {exc}"],
                    summary={"checked": len(rows), "skipped": False, "skip_reason": None},
                )
                state = "error"
            envelope = _to_envelope(tool, result)
            if use_cache:
                try:
                    write_cache(cache_dir, key, envelope)  # type: ignore[arg-type]
                except OSError:
                    pass
        _notify(progress, tool, "cache" if cache_hit else state)
        out.tools[tool] = envelope
        reports.append(envelope)
        out.tool_runs[tool] = {
            "version": envelope["version"],
            "status": envelope["status"],
            "findings": len(envelope["findings"]),
            "duration_ms": int((perf_counter() - started_tool) * 1000),
            "skipped": bool(envelope["summary"].get("skipped")),
            "skip_reason": envelope["summary"].get("skip_reason"),
            "cache_hit": cache_hit,
        }

    out.corroborated_count = _corroborate(reports)

    if "readypack" in skip:
        out.status = "success"
        out.warnings = ["readypack skipped: no aggregated findings"]
        out.finished_at = utc_now()
        out.duration_ms = int((perf_counter() - started) * 1000)
        return out

    for envelope in reports:
        if envelope["summary"].get("skipped"):
            out.warnings.append(f"{envelope['tool']}: {envelope['summary'].get('skip_reason') or 'audit skipped'}")

    rp_opts: dict[str, Any] = {
        "name": options.get("name") or options.get("dataset_name") or "dataset",
        "description": options.get("description", ""),
        "reports": reports,
        "drop_ids": options.get("drop_ids") or options.get("drop_id") or [],
        "version_tag": options.get("version_tag", "0.2.0"),
        "run_id": out.run_id,
    }
    rp_opts.update(_options_for("readypack", options))
    # Keep reports authoritative even if a user supplied their own.
    rp_opts["reports"] = reports
    try:
        rp_result = run_readypack(rows, rp_opts)
        state = "done"
    except Exception as exc:
        from readypack.common import ToolResult  # noqa: E402

        rp_result = ToolResult(status="error", findings=[], warnings=[str(exc)], summary={"checked": len(rows)})
        state = "error"
    rp_envelope = _to_envelope("readypack", rp_result)
    out.tool_runs["readypack"] = {
        "version": rp_envelope["version"],
        "status": rp_envelope["status"],
        "findings": len(rp_envelope["findings"]),
        "duration_ms": 0,
        "skipped": False,
        "skip_reason": None,
        "cache_hit": False,
    }
    out.readypack = rp_envelope
    out.findings = rp_envelope["findings"]
    out.warnings = list(rp_envelope["warnings"]) + out.warnings
    out.summary = rp_envelope["summary"]
    out.summary.setdefault("result_schema_version", RESULT_SCHEMA_VERSION)
    out.summary["run_id"] = out.run_id
    out.summary["tools_run"] = [e["tool"] for e in reports]
    out.summary["tools_skipped"] = [name for name in TOOL_NAMES if name not in out.tool_runs]
    out.summary["corroborated_findings"] = out.corroborated_count
    out.status = rp_envelope["status"]
    out.finished_at = utc_now()
    out.duration_ms = int((perf_counter() - started) * 1000)
    _notify(progress, "readypack", state)
    return out
