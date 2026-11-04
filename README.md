# HonestyPipeline

Run the entire audit family — DecayWatch, EnrichAudit, FilterGap, LinguaCheck,
NuanceBench, ReadyPack, SourceLock, and WhyChanged — as a single pipeline over
one dataset, and package the result.

The individual tools stay separate (they are included as git submodules under
`repos/`); this repository only adds an orchestrator that imports each tool's
`run()` function, collects its findings, and folds them into ReadyPack.

![Anti-Scraping Playwright](docs/banner.png)

## What the audit family checks

| Tool | Repository | What it does |
| --- | --- | --- |
| **DecayWatch** | [hexsyro/DecayWatch](https://github.com/hexsyro/DecayWatch) | Measures how much of a previously collected dataset still exists: survival rates, metadata drift, representativity, and purged records. |
| **EnrichAudit** | [hexsyro/EnrichAudit](https://github.com/hexsyro/EnrichAudit) | Finds bugs that enrichment pipelines keep shipping, such as impossible rates, mismatches, and stale fields. |
| **FilterGap** | [hexsyro/FilterGap](https://github.com/hexsyro/FilterGap) | Scores social/listening mentions with layered signals to catch spam and bots that cheap tools count as engagement. |
| **LinguaCheck** | [hexsyro/LinguaCheck](https://github.com/hexsyro/LinguaCheck) | Flags sentiment scores computed in languages the model does not actually speak. |
| **NuanceBench** | [hexsyro/NuanceBench](https://github.com/hexsyro/NuanceBench) | Scores any sentiment tool against a curated set of hard sentences (sarcasm, slang, emoji, mixed language). |
| **SourceLock** | [hexsyro/SourceLock](https://github.com/hexsyro/SourceLock) | Catches unsupported claims in AI-generated summaries relative to their source posts. |
| **WhyChanged** | [hexsyro/WhyChanged](https://github.com/hexsyro/WhyChanged) | Explains significant shifts in a tracked metric and localizes slow regime changes. |
| **ReadyPack** | [hexsyro/ReadyPack](https://github.com/hexsyro/ReadyPack) | Aggregates every finding above into a data-health score, datasheet, Croissant metadata, changelog, and human-readable report, and packages the dataset. |

## Install

```bash
git clone --recurse-submodules https://github.com/hexsyro/HonestyPipeline.git
cd HonestyPipeline
python -m pip install -e .
```

For development:

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

> The tools live as git submodules. If you cloned without `--recurse-submodules`,
> run `git submodule update --init --recursive`.

## Usage

```bash
honestypipeline dataset.csv --name "my-dataset" --out ./pack
```

Without `--out`, the ReadyPack report is printed to stdout. Pass `--config
config.json` to tune any underlying tool (top-level keys: `decaywatch`,
`enrichaudit`, `filtergap`, `linguacheck`, `nuancebench`, `sourcelock`,
`whychanged`, `readypack`, plus a `tools` object).

### Common options

| Flag | Description |
| --- | --- |
| `--format`, `-f` | Output format: `table` (default), `json`, `csv`, `md`/`markdown`. |
| `--output`, `-o` | Write the rendered report to a file instead of stdout. |
| `--out` | Write the packaged output (`cleaned.csv`, docs, `package.zip`) to a directory. |
| `--fail-on` | Exit `1` if any finding is at or above `low`/`medium`/`high` severity. |
| `--config` | JSON file of options. |
| `--name` | Dataset name for the packaged report. |
| `--description` | Dataset description. |
| `--drop-id` | Drop a reviewed row id (repeatable). |
| `--version` | Print version and exit. |

## Configuration

Options can be supplied at the top level or nested under a `tools` object:

```json
{
  "name": "my-dataset",
  "drop_ids": ["r1", "r2"],
  "tools": {
    "enrichaudit": { "max_examples": 5 },
    "linguacheck": { "language_column": "lang" }
  }
}
```

Top-level convenience keys (`name`, `description`, `drop_ids`/`drop_id`,
`dataset_name`) are forwarded to ReadyPack; per-tool sections are forwarded to
the matching tool.

## Library use

```python
from honestypipeline import run_pipeline, PipelineResult
from readypack.common import load_rows

result: PipelineResult = run_pipeline(load_rows("dataset.csv"), {"name": "demo"})
result.summary["health_score"]["score"]
```

`run_pipeline(rows, options)` returns a `PipelineResult` with:

- `status` — overall status (`"success"` or `"error"`).
- `findings` — aggregated, audit-tagged findings.
- `warnings` — aggregated warnings.
- `summary` — ReadyPack summary, including the data-health score.
- `tools` — per-tool envelopes (`decaywatch`, `enrichaudit`, …).
- `readypack` — the ReadyPack envelope.

## Output package

With `--out DIR`, HonestyPipeline writes:

- `cleaned.csv` — the dataset, minus any explicitly reviewed removals.
- `datasheet.md` — a dataset card.
- `croissant.json` — Croissant (mlcommons) metadata.
- `changelog.json` — the action history.
- `report.md` — a human-readable report.
- `package.zip` — all of the above zipped together.

Nothing is deleted silently; rows leave the export only via explicit, reviewed
`--drop-id` values, and every action is recorded in the changelog.

## Development

```bash
python -m pip install -e ".[dev]"
python -m ruff check src tests
python -m pytest
```

## License

MIT. See [LICENSE](LICENSE).
