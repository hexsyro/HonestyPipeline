"""Locate the vendored audit-tool submodules and put their src dirs on sys.path."""

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
    """Add each submodule's src directory to sys.path (idempotent)."""
    for module, dirname in _TOOL_DIRS.items():
        src = REPOS_DIR / dirname / "src"
        if src.is_dir() and str(src) not in sys.path:
            sys.path.insert(0, str(src))
    # Fallback for development outside the packaged repo layout.
    fallback_root = REPO_ROOT.parent
    for dirname in _TOOL_DIRS.values():
        src = fallback_root / dirname / "src"
        if src.is_dir() and str(src) not in sys.path:
            sys.path.insert(0, str(src))


ensure_paths()