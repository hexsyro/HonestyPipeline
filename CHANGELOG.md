# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-11-04

### Added
- Initial release: orchestrate DecayWatch, EnrichAudit, FilterGap, LinguaCheck,
  NuanceBench, ReadyPack, SourceLock, and WhyChanged as one pipeline over a
  single dataset, and package the result.
- `honestypipeline` CLI with table/json/csv/markdown output, `--out` packaging,
  `--config`, `--name`, `--description`, `--drop-id`, and `--fail-on`.
- Library entry point `run_pipeline(rows, options)` returning `PipelineResult`.
- Graceful per-tool error handling and `PipelineResult` export.
