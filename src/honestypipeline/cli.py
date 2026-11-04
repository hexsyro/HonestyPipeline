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

from honestypipeline.pipeline import PipelineResult, run_pipeline  # noqa: E402
from readypack.common import ToolResult  # noqa: E402
from readypack.export import write_package  # noqa: E402
from readypack.output import render, worst_severity  # noqa: E402

TOOL = "honestypipeline"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=TOOL,
        description="Run every audit in the family as one pipeline and package the result.",
    )
    parser.add_argument("data", help="dataset file (.csv, .json, or .jsonl)")
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
        default="none",
        help="exit 1 if any finding is at or above this severity (default: none)",
    )
    parser.add_argument("--config", metavar="FILE", help="JSON file of options")
    parser.add_argument("--name", metavar="NAME", help="dataset name for the packaged report")
    parser.add_argument("--description", metavar="TEXT", help="dataset description")
    parser.add_argument("--drop-id", action="append", metavar="ID", help="drop a reviewed row id; repeatable")
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
    return options


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        options = _merge_options(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
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

    result: PipelineResult = run_pipeline(rows, options)
    tool_result = ToolResult(
        status=result.status,
        findings=result.findings,
        warnings=result.warnings,
        summary=result.summary,
    )

    if args.out:
        try:
            archive = write_package(
                args.out,
                rows=rows,
                summary=result.summary,
                drop_ids=options.get("drop_ids"),
            )
        except OSError as exc:
            print(f"{TOOL}: could not write package: {exc}", file=sys.stderr)
            return 2
        print(f"{TOOL}: package written to {archive}")

    text = render(tool_result, args.format, tool=TOOL, version=__version__)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="" if text.endswith("\n") else "\n")

    if args.fail_on != "none":
        worst = worst_severity(tool_result)
        from readypack.common import SEVERITY_RANK  # noqa: E402

        if worst and SEVERITY_RANK.get(worst, 0) >= SEVERITY_RANK[args.fail_on]:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())