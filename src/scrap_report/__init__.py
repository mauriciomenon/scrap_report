"""Public package surface for importers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .contract import (
    CLI_ENTRYPOINT,
    EXPORT_CONTRACTS,
    IMPORT_NAME,
    MINIMUM_FIELDS_BY_FLOW,
    MODULE_ENTRYPOINT,
    PACKAGE_NAME,
    PACKAGE_VERSION,
    PREFERRED_CONTRACTS,
    PRODUCER,
    SCHEMA_REQUIRED_FIELDS,
    SCHEMA_VERSION,
    build_contract_catalog,
    utc_now_iso,
    validate_contract_definition,
    validate_payload_schema,
)

if TYPE_CHECKING:
    from .config import ScrapeConfig
    from .pipeline import PipelineResult, run_pipeline

__version__ = PACKAGE_VERSION

__all__ = [
    "__version__",
    "PACKAGE_NAME",
    "PACKAGE_VERSION",
    "IMPORT_NAME",
    "CLI_ENTRYPOINT",
    "MODULE_ENTRYPOINT",
    "SCHEMA_VERSION",
    "PRODUCER",
    "EXPORT_CONTRACTS",
    "PREFERRED_CONTRACTS",
    "MINIMUM_FIELDS_BY_FLOW",
    "SCHEMA_REQUIRED_FIELDS",
    "build_contract_catalog",
    "validate_contract_definition",
    "validate_payload_schema",
    "utc_now_iso",
    "ScrapeConfig",
    "PipelineResult",
    "run_pipeline",
]


def __getattr__(name: str) -> Any:
    if name == "ScrapeConfig":
        from .config import ScrapeConfig

        return ScrapeConfig
    if name in {"PipelineResult", "run_pipeline"}:
        from .pipeline import PipelineResult, run_pipeline

        return {
            "PipelineResult": PipelineResult,
            "run_pipeline": run_pipeline,
        }[name]
    raise AttributeError(f"module {IMPORT_NAME!r} has no attribute {name!r}")
