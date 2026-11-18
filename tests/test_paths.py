from pathlib import Path

from honestypipeline._paths import REPOS_DIR, ensure_paths


def test_submodule_sources_take_priority_over_siblings():
    """Sibling development checkouts must never shadow pinned submodules."""
    ensure_paths()
    import readypack

    assert Path(readypack.__file__).resolve().is_relative_to(REPOS_DIR.resolve())
