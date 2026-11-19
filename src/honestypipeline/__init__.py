"""HonestyPipeline - run the whole audit family as one pipeline."""

from honestypipeline._paths import ensure_paths

ensure_paths()

from honestypipeline import pipeline as _pipeline  # noqa: E402
from honestypipeline.manifest import RESULT_SCHEMA_VERSION, build_run_manifest  # noqa: E402

__version__ = "0.2.0"
__all__ = [
    "__version__",
    "RESULT_SCHEMA_VERSION",
    "PipelineResult",
    "run_pipeline",
    "build_run_manifest",
]

PipelineResult = _pipeline.PipelineResult
run_pipeline = _pipeline.run_pipeline
