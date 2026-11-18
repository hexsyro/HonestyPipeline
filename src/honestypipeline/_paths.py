"""Locate the vendored audit-tool submodules and put their src dirs on sys.path.

Submodule sources always take precedence over sibling development checkouts.
The sibling fallback exists for working outside the packaged layout, but must
never shadow the versions pinned by this repository.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REPOS_DIR = REPO_ROOT / "repos"

_TOOL_DIRS = {
    "decaywatch": "DecayWatch",
    "enrichaudit": "EnrichAudit",
    "filtergap": "FilterGap",
    "linguacheck": "LinguaCheck",
    "nuancebench": "NuanceBench",
    "readypack": "ReadyPack",
    "sourcelock": "SourceLock",
    "whychanged": "WhyChanged",
}


def ensure_paths() -> None:
    """Add tool src directories to sys.path with submodules first (idempotent)."""
    sources: list[str] = []
    fallbacks: list[str] = []

    for dirname in _TOOL_DIRS.values():
        src = REPOS_DIR / dirname / "src"
        if src.is_dir():
            sources.append(str(src))

    fallback_root = REPO_ROOT.parent
    for dirname in _TOOL_DIRS.values():
        src = fallback_root / dirname / "src"
        if src.is_dir():
            fallbacks.append(str(src))

    # Re-insert in priority order: lower priority first so it ends up last.
    for path in list(reversed(fallbacks)) + list(reversed(sources)):
        if path in sys.path:
            sys.path.remove(path)
        sys.path.insert(0, path)


ensure_paths()
