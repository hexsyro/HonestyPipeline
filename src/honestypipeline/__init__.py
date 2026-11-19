"""HonestyPipeline - run the whole audit family as one pipeline."""

from honestypipeline._paths import ensure_paths

ensure_paths()

from honestypipeline import pipeline as _pipeline
from honestypipeline.manifest import RESULT_SCHEMA_VERSION, build_run_manifest

__version__ = "0.2.0"
__all__ = [
    "RESULT_SCHEMA_VERSION",
    "PipelineResult",
    "__version__",
    "build_run_manifest",
    "run_pipeline",
]

PipelineResult = _pipeline.PipelineResult
run_pipeline = _pipeline.run_pipeline
