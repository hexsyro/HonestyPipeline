# HonestyPipeline v0.2.0 — Release Notes

**Released:** 2026-11-19  
**Theme:** trust, observability, and reproducibility across the audit family.

This is a coordinated release: all eight standalone tools (the `repos/`
submodules) and the orchestrator move from `0.1.0` to `0.2.0` together. Public
entry points (`run(rows, options) -> ToolResult`, `run_pipeline(...)`, the
`honestypipeline` CLI) remain backward compatible.

---

## Why these upgrades

Before writing code we did a deep pass over current standards, articles, and
community discussions. Five findings shaped this release:

1. **Documentation is now an audit trail.** Croissant 1.1 (Feb 2026) adds W3C
   PROV-O chain-of-custody, requires semantic versions and file checksums, and
   is already used by ~700K datasets including Common Crawl
   ([MLCommons](https://mlcommons.org/2026/02/croissant-1-1-standard),
   [spec](https://docs.mlcommons.org/croissant/docs/croissant-spec-1.0.html)).
   Croissant-RAI folds in Data Cards / Datasheets concepts
   ([NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/file/9547b09b722f2948ff3ddb5d86002bc0-Paper-Datasets_and_Benchmarks_Track.pdf)).
   → ReadyPack emits provenance, checksums, datasheet JSON, and JSON-LD.

2. **Silent failure is the top real-world complaint.** In HN's "Get me out of
   data hell" (698 points), users describe pipelines that "fail completely
   silently" and teams that "wrap every API call in a try/catch and then ignore
   the errors" ([HN](https://news.ycombinator.com/item?id=42010249)). A robotics
   dataset launch repeats the pain: "difficult to know which code ran, why an
   episode was excluded, or whether a dataset can be reproduced"
   ([HN](https://news.ycombinator.com/item?id=49510632)).
   → Every tool now reports skipped/no-op state and a shared result schema;
   the orchestrator writes a `run.json` manifest.

3. **Coverage beats capability, and rules must be queryable.** The 2026 data
   quality landscape argues that hand-authoring every check never scales and
   that generated tests from profiling are the way forward
   ([DataKitchen](https://datakitchen.io/blog/the-2026-open-source-data-quality-and-data-observability-landscape)).
   The tooling comparison stresses storing a queryable `check_results` table
   and pruning rules that never fire
   ([IcebergLakehouse](https://iceberglakehouse.com/posts/data-quality-tooling-compared)).
   → EnrichAudit gains profiling, a results ledger, and conflict detection;
   DecayWatch gains survival curves instead of a single endpoint.

4. **Groundedness is claim-level, not similarity-level.** RAGAS and FActScore
   decompose answers into atomic claims and verify each against context
   ([RAGAS walkthrough](https://www.youtube.com/watch?v=xsDNArrmyuo),
   [FActScore survey](https://aman.ai/primers/ai/factuality-in-LLMs)); a 1–5
   rubric with explanations is a 2025 NAACL finding
   ([ACL](https://aclanthology.org/2025.findings-naacl.433)). NLI still fails
   on implicit/multi-hop contradictions
   ([2026 survey](https://www.sciencedirect.com/science/article/pii/S2949719126000361)),
   so we report three signals and label the method's limits honestly.
   → SourceLock adds atomic subclaims, numeric conflicts, and
   entailment/contradiction/missing-evidence signals.

5. **Hard-case NLP needs per-slice metrics and versioned probe sets.**
   Code-switching errors cascade into sentiment and NER
   ([Deepgram](https://deepgram.com/blog/what-is-code-switching-asr-guide));
   code-switched benchmarks add explicit "mixed" classes
   ([COSMUS](https://aclanthology.org/2025.unlp-1.18.pdf)); a large share of
   apparent LID errors can actually be bad gold labels
   ([JOHD](https://openhumanitiesdata.metajnl.com/articles/10.5334/johd.44)).
   → LinguaCheck emits language distributions and coverage matrices;
   NuanceBench ships hashed, per-item probe results and regression mode.

CLI/UX decisions follow the "CLI as API" guidance: stdout is the machine
contract, diagnostics go to stderr, exit codes are stable and documented, and
`main(argv)` stays testable
([CLI best practices](https://hackmd.io/@arturtamborski/cli-best-practices),
[Vercel CLI guidelines](https://vercel.com/design/cli)).

---

## What changed in each tool

| Tool | Highlights in v0.2.0 |
| --- | --- |
| **DecayWatch** | Survival curve (day 0/30/90/365), half-life and annualized loss; content/reference-rot detection; source-type risk stratification; chi-square expected-count guard; configurable drift and text columns; broken template CI removed. |
| **EnrichAudit** | Profiling mode generating an enrichment contract; JSONL check-results ledger; golden-record conflict detection; malformed-row warnings; all-column Benford screening; fixed rate-tolerance tiers. |
| **FilterGap** | First-class per-signal explanations and `--explain`; calibration metrics when labels exist; automation vs harm scores; verified accounts honored in the ML layer; scalable coordinated-cluster candidate generation; ASCII-only entropy guard. |
| **LinguaCheck** | `--min-confidence`; per-record language distributions and `mixed_language_unscorable` findings; model coverage matrix; ISO-639-3 normalization; Unicode-script code-switch detection; honest runner-up/margin and short-text confidence. |
| **NuanceBench** | Version `2026.11` with SHA-256 hashed probe set; per-item results with probe ids; custom probes, category filters, `--list-probes`; expanded negation/intensifier/typo taxonomy; `--baseline --regression` CI gate. |
| **SourceLock** | Atomic subclaim decomposition with targeted unsupported-subclaim findings; numeric/date contradictions across all source chunks; entailment/contradiction/missing-evidence signals with documented limitations; stopword filtering; `--min-claim-chars`. |
| **WhyChanged** | Change-point confidence, settling window, and segment means; deduplicated step/regime findings; top-contributor drill-down (never labelled "cause"); absolute-delta handling for zero baselines; UTC-correct date sorting. |
| **ReadyPack** | Croissant 1.1-style metadata with `conformsTo`, inferred field types, SHA-256 checksums and PROV-O provenance; `datasheet.json`, `dataset.jsonld`, `findings.json`; transparent health-score components and FAIR self-assessment; `extra_files` support for `run.json`. |
| **HonestyPipeline** | `run.json` manifests, `--only`/`--skip`/`--list-tools`, content-addressed cache, baseline regression gate, cross-tool corroboration, versioned JSON output, exit codes 0/1/2/3/130, Python 3.14 CI. |

---

## Shared v0.2.0 result contract

Every tool now exports:

- `RESULT_SCHEMA_VERSION = "1.1"`
- `ToolResult` from its package root
- `summary["result_schema_version"] == "1.1"`
- `summary["skipped"]` and `summary["skip_reason"]` so a no-op audit is no
  longer indistinguishable from a clean one

Config values are validated with the shared `opt_float`/`opt_int`/`opt_list`
helpers; malformed config returns exit code 2 instead of a traceback.

---

## Compatibility and upgrading

- No new runtime dependencies; Python >= 3.10 remains the floor.
- Existing `run(rows, options)` calls keep working; new options are additive.
- `--format json` output now has extra top-level keys (`schemaVersion`, `run`);
  existing consumers reading `findings`, `warnings`, and `summary` are unaffected.
- Update submodules after pulling:
  `git submodule update --init --recursive`.
- Rebuild the distribution: `python -m build`.

## Verification

Each repository's release checklist was:

```bash
python -m pytest -q
python -m ruff check src tests
python -m pyright src
python -m build
```

The orchestrator additionally exercises all eight audit envelopes end to end.
