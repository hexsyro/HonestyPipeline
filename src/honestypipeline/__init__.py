"""HonestyPipeline - run the whole audit family as one pipeline."""

from honestypipeline._paths import ensure_paths

ensure_paths()

from honestypipeline import pipeline as _pipeline  # noqa: E402

__version__ = "0.1.0"
__all__ = ["__version__", "run_pipeline"]

run_pipeline = _pipeline.run_pipeline