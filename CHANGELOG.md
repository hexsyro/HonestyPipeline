# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-11-19

### Added
- Run manifests (`run.json`) with input SHA-256, row fingerprint, run id,
  timestamps, per-tool durations/statuses, resolved options, and tool versions;
  shipped inside `package.zip` and included in `--format json` output.
- Tool selection with `--only` / `--skip` and per-tool `enabled` config flags;
  `--list-tools` prints the available audits and versions.
- Content-addressed audit cache (`--cache-dir`, `--no-cache`) keyed by input
  fingerprint + tool version + tool options.
- Baseline regression gating with `--baseline` / `--fail-on-regression`
  (health-score delta and new high-severity findings).
- Cross-tool corroboration: findings sharing a `record_id` + `field` are tagged
  with the corroborating tools in `metadata.corroboration`.
- Documented exit codes (`0` ok, `1` gate/regression, `2` usage/input error,
  `3` audit error, `130` interrupt), `--version-tag` for Croissant metadata,
  `--explain`, `--quiet`, and `@args.txt` argument files.
- `RESULT_SCHEMA_VERSION = "1.1"` shared contract across the orchestrator and
  all eight tools; `result_schema_version`, `skipped`, and `skip_reason` in
  every tool envelope summary.
- Full release notes with research sources in `docs/RELEASE_NOTES_v0.2.0.md`.

### Changed
- `--format json` emits a versioned machine contract (`schemaVersion`, `run`,
  `findings`, `summary`, `tools`) with diagnostics kept on stderr.
- `--out` plus JSON no longer corrupts stdout with the package message.
- Python 3.14 added to the CI test matrix.

### Inspiration
- Croissant 1.1 provenance: https://mlcommons.org/2026/02/croissant-1-1-standard
- "Which code ran / can this be reproduced": https://news.ycombinator.com/item?id=49510632
- CLI as API: https://hackmd.io/@arturtamborski/cli-best-practices
- Write-audit-publish and quality gates: https://iceberglakehouse.com/posts/data-quality-tooling-compared

## [0.1.0] - 2026-11-04

### Added
- Initial release: orchestrate DecayWatch, EnrichAudit, FilterGap, LinguaCheck,
  NuanceBench, ReadyPack, SourceLock, and WhyChanged as one pipeline over a
  single dataset, and package the result.
- `honestypipeline` CLI with table/json/csv/markdown output, `--out` packaging,
  `--config`, `--name`, `--description`, `--drop-id`, and `--fail-on`.
- Library entry point `run_pipeline(rows, options)` returning `PipelineResult`.
- Graceful per-tool error handling and `PipelineResult` export.
