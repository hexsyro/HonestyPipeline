# Contributing

Thanks for considering a contribution to HonestyPipeline.

## Ground rules

- **Keep it stdlib-only at runtime.** The orchestrator itself has no third-party
  runtime dependencies; install the submodules via `git submodule update --init`.
- **Tests must pass.** Run `python -m pytest` before submitting.
- **Lint must be clean.** Run `ruff check src tests`.

## Development setup

```bash
git clone --recurse-submodules https://github.com/hexsyro/HonestyPipeline.git
cd HonestyPipeline
python -m pip install -e ".[dev]"
python -m pytest
```

## Submitting changes

Open a pull request against `main` with a clear description of the change and
the motivation behind it.
