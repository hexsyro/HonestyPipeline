# HonestyPipeline

Run the whole audit family - DecayWatch, EnrichAudit, FilterGap, LinguaCheck,
NuanceBench, ReadyPack, SourceLock, and WhyChanged - as one pipeline over a
single dataset, and package the result.

The individual tools stay separate (they are included as git submodules under
`repos/`); this repository only adds an orchestrator that imports each tool's
`run()` function, collects its findings, and folds them into ReadyPack.

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

## Usage

```bash
honestypipeline dataset.csv --name "my-dataset" --out ./pack
```

Without `--out`, it prints the ReadyPack report. Pass `--config config.json` to tune
any underlying tool (keys: `decaywatch`, `enrichaudit`, `filtergap`,
`linguacheck`, `nuancebench`, `sourcelock`, `whychanged`, `readypack`, plus a
`tools` object).

## Library use

```python
from honestypipeline import run_pipeline
from readypack.common import load_rows

result = run_pipeline(load_rows("dataset.csv"), {"name": "demo"})
result.summary["health_score"]["score"]
```

## License

MIT.