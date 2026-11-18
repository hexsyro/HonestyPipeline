"""Reproducibility helpers: fingerprints, run manifests, caching, baselines.

Everything in this module is stdlib-only and side-effect free except the small
cache helpers, which write JSON files under an explicitly supplied directory.
The manifest is the ``run.json`` document shipped inside ReadyPack packages; it
answers the question "which code ran, on which bytes, with which options?".
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RESULT_SCHEMA_VERSION = "1.1"


def utc_now() -> str:
    """UTC timestamp in ISO-8601 form, second precision."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fingerprint_rows(rows: list[dict]) -> str:
    """Stable SHA-256 over normalized row content (order matters, keys do not)."""
    payload = json.dumps(
        rows,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fingerprint_file(path: str | Path) -> str:
    """SHA-256 of a file's raw bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def sanitize_options(options: dict[str, Any]) -> dict[str, Any]:
    """Drop orchestrator-only/volatile keys from a manifest's options block."""
    skip = {"progress", "reports", "cache_dir", "no_cache", "baseline", "fail_on_regression"}
    return _json_safe({k: v for k, v in options.items() if k not in skip})


def build_run_manifest(
    *,
    version: str,
    result: Any,
    options: dict[str, Any],
    rows_count: int,
    input_path: str | None = None,
    input_sha256: str | None = None,
    rows_sha256: str | None = None,
) -> dict[str, Any]:
    """Build the ``run.json`` provenance document for one pipeline run."""
    tool_runs = _json_safe(getattr(result, "tool_runs", {}) or {})
    manifest: dict[str, Any] = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "tool": "honestypipeline",
        "version": version,
        "run_id": getattr(result, "run_id", ""),
        "started_at": getattr(result, "started_at", ""),
        "finished_at": getattr(result, "finished_at", ""),
        "duration_ms": getattr(result, "duration_ms", 0),
        "status": getattr(result, "status", "success"),
        "input": {
            "path": input_path,
            "sha256": input_sha256,
            "rows_sha256": rows_sha256,
            "rows": rows_count,
        },
        "options": sanitize_options(options),
        "tools": tool_runs,
        "health_score": (getattr(result, "summary", {}) or {}).get("health_score", {}),
        "warnings": list(getattr(result, "warnings", []) or []),
    }
    return manifest


def cache_key(*, fingerprint: str, tool: str, version: str, options: dict[str, Any]) -> str:
    """Content-addressed cache key: input bytes + tool version + tool options."""
    payload = json.dumps(
        {"schema": RESULT_SCHEMA_VERSION, "fingerprint": fingerprint, "tool": tool,
         "version": version, "options": _json_safe(options)},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_cache(directory: str | Path, key: str) -> dict[str, Any] | None:
    """Read a cached tool envelope, or None when absent/corrupt."""
    path = Path(directory) / f"{key}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_cache(directory: str | Path, key: str, envelope: dict[str, Any]) -> None:
    """Atomically write a cached tool envelope."""
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{key}.json"
    tmp = root / f".{key}.{os.getpid()}.tmp"
    tmp.write_text(
        json.dumps(envelope, sort_keys=True, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    tmp.replace(path)


def compare_baseline(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    """Compare a current result with a previous ``--format json`` document.

    Both sides may be a full CLI JSON envelope (``{"summary": ..., "findings": ...}``)
    or a bare summary dict. Missing values are treated as zero and reported.
    """
    cur_summary = current.get("summary", {}) if isinstance(current, dict) else {}
    base_summary = baseline.get("summary", {}) if isinstance(baseline, dict) else {}
    if not isinstance(cur_summary, dict):
        cur_summary = {}
    if not isinstance(base_summary, dict):
        base_summary = {}

    def score(s: dict[str, Any]) -> float:
        health = s.get("health_score", {})
        if isinstance(health, dict):
            try:
                return float(health.get("score", 0) or 0)
            except (TypeError, ValueError):
                return 0.0
        return 0.0

    def high_ids(doc: dict[str, Any]) -> set[str]:
        found: set[str] = set()
        for item in doc.get("findings", []) if isinstance(doc, dict) else []:
            if not isinstance(item, dict) or str(item.get("severity", "")).lower() != "high":
                continue
            key = str(item.get("record_id") or item.get("field") or item.get("message") or id(item))
            found.add(key)
        return found

    score_after = score(cur_summary)
    score_before = score(base_summary)
    before = high_ids(baseline)
    after = high_ids(current)
    new_high = sorted(after - before)
    delta = round(score_after - score_before, 2)
    return {
        "score_before": score_before,
        "score_after": score_after,
        "score_delta": delta,
        "high_before": len(before),
        "high_after": len(after),
        "new_high_findings": new_high[:50],
        "new_high_count": len(new_high),
        "regressed": delta < 0 or bool(new_high),
    }
