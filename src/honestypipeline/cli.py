"""Command-line interface for HonestyPipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from honestypipeline import __version__
from honestypipeline._paths import ensure_paths

ensure_paths()

from honestypipeline.manifest import (  # noqa: E402
    build_run_manifest,
    compare_baseline,
    fingerprint_file,
)
from honestypipeline.pipeline import TOOL_NAMES, TOOL_VERSIONS, PipelineResult, run_pipeline  # noqa: E402
from readypack.common import ToolResult  # noqa: E402
from readypack.export import write_package  # noqa: E402
from readypack.output import render, worst_severity  # noqa: E402

TOOL = "honestypipeline"

EXIT_CODE_HELP = """exit codes:
  0  audit completed (no gate tripped)
  1  --fail-on threshold met, or --fail-on-regression detected a regression
  2  usage, config, or input error
  3  one or more audit tools errored
  130 interrupted (Ctrl+C)
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=TOOL,
        description="Run every audit in the family as one pipeline and package the result.",
        epilog=EXIT_CODE_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
        fromfile_prefix_chars="@",
    )
    parser.add_argument("data", nargs="?", help="dataset file (.csv, .json, or .jsonl)")
    parser.add_argument(
        "--format",
        "-f",
        choices=["table", "json", "csv", "md", "markdown"],
        default="table",
        help="output format (default: table)",
    )
    parser.add_argument("--output", "-o", metavar="FILE", help="write the report to FILE instead of stdout")
    parser.add_argument("--out", metavar="DIR", help="write the packaged output (cleaned.csv + docs + package.zip) to DIR")
    parser.add_argument(
        "--fail-on",
        choices=["none", "low", "medium", "high"],
        type=str.lower,
        default="none",
        help="exit 1 if any finding is at or above this severity (default: none)",
    )
    parser.add_argument("--config", metavar="FILE", help="JSON file of options")
    parser.add_argument("--name", metavar="NAME", help="dataset name for the packaged report")
    parser.add_argument("--description", metavar="TEXT", help="dataset description")
    parser.add_argument("--drop-id", action="append", metavar="ID", help="drop a reviewed row id; repeatable")
    parser.add_argument("--version-tag", metavar="TAG", help="dataset version for Croissant metadata (default: 0.2.0)")
    parser.add_argument("--only", metavar="TOOLS", help="run only these comma-separated tools")
    parser.add_argument("--skip", metavar="TOOLS", help="skip these comma-separated tools")
    parser.add_argument("--list-tools", action="store_true", help="list available audit tools and versions")
    parser.add_argument("--cache-dir", metavar="DIR", help="cache audit envelopes by input+version+options")
    parser.add_argument("--no-cache", action="store_true", help="ignore cached audit envelopes")
    parser.add_argument("--baseline", metavar="FILE", help="previous --format json result to compare against")
    parser.add_argument("--fail-on-regression", action="store_true", help="exit 1 if the baseline comparison regresses")
    parser.add_argument("--quiet", "-q", action="store_true", help="suppress progress messages on stderr")
    parser.add_argument("--explain", action="store_true", help="show FilterGap signal explanations in table output")
    parser.add_argument("--version", action="version", version=f"{TOOL} {__version__}")
    return parser


def _merge_options(args: argparse.Namespace) -> dict[str, Any]:
    options: dict[str, Any] = {}
    if args.config:
        parsed = json.loads(Path(args.config).read_text(encoding="utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError(f"{args.config}: config must be a JSON object")
        options.update(parsed)
    if args.name is not None:
        options["name"] = args.name
    if args.description is not None:
        options["description"] = args.description
    if args.drop_id:
        options["drop_ids"] = list(options.get("drop_ids") or []) + args.drop_id
    if args.version_tag is not None:
        options["version_tag"] = args.version_tag
    if args.only is not None:
        options["only"] = args.only
    if args.skip is not None:
        options["skip"] = args.skip
    if args.cache_dir is not None:
        options["cache_dir"] = args.cache_dir
    if args.no_cache:
        options["no_cache"] = True
    if args.explain:
        options.setdefault("tools", {}).setdefault("filtergap", {})["explain"] = True
    return options


def _print_tools() -> None:
    width = max(len(name) for name in TOOL_NAMES)
    print(f"{'tool':<{width}}  version")
    print(f"{'-' * width}  {'-' * 7}")
    for name in TOOL_NAMES:
        print(f"{name:<{width}}  {TOOL_VERSIONS[name]}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list_tools:
        _print_tools()
        return 0
    if not args.data:
        parser.error("the following arguments are required: data")

    try:
        options = _merge_options(args)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"{TOOL}: {exc}", file=sys.stderr)
        return 2
    from readypack.common import load_rows  # noqa: E402

    try:
        rows = load_rows(args.data)
    except FileNotFoundError:
        print(f"{TOOL}: file not found: {args.data}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"{TOOL}: {exc}", file=sys.stderr)
        return 2

    def progress(tool: str, state: str) -> None:
        if not args.quiet:
            print(f"{TOOL}: {tool}: {state}", file=sys.stderr)

    try:
        result: PipelineResult = run_pipeline(rows, options, progress=progress if not args.quiet else None)
    except (ValueError, TypeError) as exc:
        print(f"{TOOL}: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print(f"{TOOL}: interrupted", file=sys.stderr)
        return 130

    file_hash: str | None = None
    try:
        file_hash = fingerprint_file(args.data)
    except OSError:
        pass
    manifest = build_run_manifest(
        version=__version__,
        result=result,
        options=options,
        rows_count=len(rows),
        input_path=args.data,
        input_sha256=file_hash,
        rows_sha256=result.input_fingerprint,
    )

    if args.out:
        extra = {"run.json": json.dumps(manifest, indent=2, ensure_ascii=False, default=str)}
        try:
            try:
                archive = write_package(
                    args.out,
                    rows=rows,
                    summary=result.summary,
                    drop_ids=options.get("drop_ids"),
                    extra_files=extra,
                )
            except TypeError:  # older ReadyPack without extra_files support
                archive = write_package(
                    args.out,
                    rows=rows,
                    summary=result.summary,
                    drop_ids=options.get("drop_ids"),
                )
            (Path(args.out) / "run.json").write_text(extra["run.json"], encoding="utf-8")
        except OSError as exc:
            print(f"{TOOL}: could not write package: {exc}", file=sys.stderr)
            return 2
        message = f"{TOOL}: package written to {archive}"
        if args.format == "json":
            print(message, file=sys.stderr)
        else:
            print(message)
            print()

    if args.format == "json":
        payload = {
            "tool": TOOL,
            "version": __version__,
            "schemaVersion": manifest["schema_version"],
            "status": result.status,
            "run": manifest,
            "findings": result.findings,
            "warnings": result.warnings,
            "summary": result.summary,
            "tools": result.tools,
        }
        text = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    else:
        tool_result = ToolResult(
            status=result.status,
            findings=result.findings,
            warnings=result.warnings,
            summary=result.summary,
        )
        text = render(tool_result, args.format, tool=TOOL, version=__version__)

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="" if text.endswith("\n") else "\n")

    regressed = False
    if args.baseline:
        try:
            baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"{TOOL}: could not read baseline: {exc}", file=sys.stderr)
            return 2
        current_doc = {"summary": result.summary, "findings": result.findings}
        comparison = compare_baseline(current_doc, baseline)
        regressed = bool(comparison["regressed"])
        print(
            f"{TOOL}: baseline score {comparison['score_before']} -> {comparison['score_after']} "
            f"({comparison['score_delta']:+}), new high findings: {comparison['new_high_count']}",
            file=sys.stderr,
        )

    gate_tripped = False
    if args.fail_on != "none":
        tool_result = ToolResult(status=result.status, findings=result.findings, warnings=result.warnings)
        worst = worst_severity(tool_result)
        from readypack.common import SEVERITY_RANK  # noqa: E402

        if worst and SEVERITY_RANK.get(str(worst).lower(), 0) >= SEVERITY_RANK[args.fail_on.lower()]:
            gate_tripped = True

    tool_error = any(env.get("status") == "error" for env in result.tools.values()) or result.readypack.get("status") == "error"
    if tool_error:
        return 3
    if gate_tripped or (args.fail_on_regression and regressed):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
