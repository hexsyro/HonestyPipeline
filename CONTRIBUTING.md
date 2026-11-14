# Contributing

Thanks for considering a contribution to HonestyPipeline.

## Ground rules

- **Keep it stdlib-only at runtime.** The orchestrator itself has no third-party
  runtime dependencies; install the submodules via `git submodule update --init`.
- **Tests must pass.** Run `python -m pytest` before submitting.
- **Lint must be clean.** Run `ruff check src tests`.
- **Type checks must pass.** Run `pyright src` before submitting.
- **Run the GitHub workflow tests.** The repository's CI workflow
  (`.github/workflows/ci.yml`) runs lint, type checks, tests, and a build on
  every pull request. Run the same commands locally before opening a PR so
  pull-request bugs are caught early:
  `ruff check src tests`, `pyright src`, `python -m pytest`, and
  `python -m build`.

## Development setup

```bash
git clone --recurse-submodules https://github.com/hexsyro/HonestyPipeline.git
cd HonestyPipeline
git submodule update --init --recursive
python -m pip install -e ".[dev]"
ruff check src tests
pyright src
python -m pytest
```

## Submitting changes

Before opening a pull request, run the workflow tests above (the same checks the
GitHub Actions CI workflow runs) and make sure they all pass. Contributors must
run the workflow tests before make pull requests. Then open a pull
request against `main` with a clear description of the change and the
motivation behind it.
