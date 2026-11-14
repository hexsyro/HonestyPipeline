## Summary

Describe the change and the motivation behind it.

## Checklist

- [ ] Submodules initialized (`git submodule update --init --recursive`)
- [ ] Ran the GitHub workflow tests locally before opening this PR:
  - [ ] `ruff check src tests`
  - [ ] `pyright src`
  - [ ] `python -m pytest`
  - [ ] `python -m build`
- [ ] Lint, type checks, tests, and build all pass