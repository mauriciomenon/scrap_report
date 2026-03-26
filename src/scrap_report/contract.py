"""Contrato de saida JSON para integracao externa."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

PACKAGE_NAME = "scrap-report"
PACKAGE_VERSION = "0.1.17"
IMPORT_NAME = "scrap_report"
CLI_ENTRYPOINT = "scrap-report"
MODULE_ENTRYPOINT = "python -m scrap_report.cli"

SCHEMA_VERSION = "1.0.0"
PRODUCER = "scrap_report.cli"

EXPORT_CONTRACTS: dict[str, dict[str, str]] = {
    "playwright_reports": {
        "dados": "data_xlsx",
        "estatisticas": "summary_xlsx",
        "relatorio_txt": "report_txt",
    },
    "rest_reports": {
        "csv": "data_csv",
        "xlsx": "data_xlsx",
        "summary_xlsx": "summary_xlsx",
        "manifest_json": "manifest_json",
    },
}

PREFERRED_CONTRACTS: dict[str, dict[str, str]] = {
    "sam_api": {
        "schema": "sam_api_result",
        "export_contract": "rest_reports",
    },
    "sam_api_flow": {
        "schema": "sam_api_result",
        "export_contract": "rest_reports",
    },
    "sam_api_standalone": {
        "schema": "sam_api_flow_result",
        "export_contract": "rest_reports",
    },
    "sweep_run_rest": {
        "schema": "sweep_result",
        "export_contract": "rest_reports",
    },
    "report_from_excel": {
        "schema": "report_result",
        "export_contract": "playwright_reports",
    },
}

MINIMUM_FIELDS_BY_FLOW: dict[str, list[str]] = {
    "sam_api": [
        "status",
        "mode",
        "runtime_mode",
        "count",
        "telemetry",
        "exports",
        "manifest_json",
    ],
    "sam_api_flow": [
        "status",
        "profile",
        "mode",
        "runtime_mode",
        "count",
        "telemetry",
        "exports",
        "manifest_json",
        "summary",
    ],
    "sam_api_standalone": [
        "status",
        "profile",
        "mode",
        "runtime_mode",
        "count",
        "output_dir",
        "telemetry",
        "exports",
        "manifest_json",
        "summary",
    ],
    "sweep_run_rest": [
        "status",
        "report_kind",
        "scope_mode",
        "runtime_mode",
        "item_count",
        "success_count",
        "failure_count",
        "items",
        "manifest_json",
    ],
    "report_from_excel": [
        "status",
        "reports",
    ],
}

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

SCHEMA_REQUIRED_FIELDS: dict[str, set[str]] = {
    "scrape_result": {
        "status",
        "report_kind",
        "downloaded_path",
        "started_at",
        "finished_at",
    },
    "pipeline_result": {
        "status",
        "report_kind",
        "source_path",
        "staged_path",
        "reports",
    },
    "stage_result": {
        "status",
        "staged_path",
    },
    "report_result": {
        "status",
        "reports",
    },
    "contract_info": {
        "status",
        "contract",
    },
    "secret_result": {
        "status",
    },
    "scan_result": {
        "status",
        "findings_count",
        "findings",
    },
    "sam_api_result": {
        "status",
        "mode",
        "runtime_mode",
        "count",
        "items",
        "telemetry",
        "exports",
        "manifest_json",
        "filters",
        "warnings",
        "verify_tls",
        "timeout_seconds",
    },
    "sam_api_flow_result": {
        "status",
        "profile",
        "runtime_mode",
        "count",
        "output_dir",
        "telemetry",
        "exports",
        "manifest_json",
        "summary",
        "mode",
        "filters",
        "warnings",
        "verify_tls",
        "timeout_seconds",
    },
    "sweep_result": {
        "status",
        "report_kind",
        "scope_mode",
        "runtime_mode",
        "item_count",
        "success_count",
        "failure_count",
        "items",
        "manifest_json",
    },
}


def validate_contract_definition() -> None:
    """Valida configuracao estatica do contrato."""
    if not SEMVER_RE.match(SCHEMA_VERSION):
        raise ValueError("SCHEMA_VERSION invalido: esperado formato semver X.Y.Z")
    if not PRODUCER.strip():
        raise ValueError("PRODUCER nao pode ser vazio")
    if not SCHEMA_REQUIRED_FIELDS:
        raise ValueError("SCHEMA_REQUIRED_FIELDS nao pode ser vazio")
    if not EXPORT_CONTRACTS:
        raise ValueError("EXPORT_CONTRACTS nao pode ser vazio")
    if not PREFERRED_CONTRACTS:
        raise ValueError("PREFERRED_CONTRACTS nao pode ser vazio")
    if not MINIMUM_FIELDS_BY_FLOW:
        raise ValueError("MINIMUM_FIELDS_BY_FLOW nao pode ser vazio")


def build_contract_catalog() -> dict[str, Any]:
    """Retorna catalogo de discovery para consumo externo."""
    validate_contract_definition()
    return {
        "package": {
            "package_name": PACKAGE_NAME,
            "package_version": PACKAGE_VERSION,
            "import_name": IMPORT_NAME,
            "cli_entrypoint": CLI_ENTRYPOINT,
            "module_entrypoint": MODULE_ENTRYPOINT,
        },
        "schema_version": SCHEMA_VERSION,
        "producer": PRODUCER,
        "schemas": {
            name: sorted(fields)
            for name, fields in SCHEMA_REQUIRED_FIELDS.items()
        },
        "exports": EXPORT_CONTRACTS,
        "preferred_contracts": PREFERRED_CONTRACTS,
        "minimum_fields_by_flow": MINIMUM_FIELDS_BY_FLOW,
    }


def validate_payload_schema(schema_name: str, payload: dict[str, Any]) -> None:
    """Valida payload antes de serializar para consumo externo."""
    required = SCHEMA_REQUIRED_FIELDS.get(schema_name)
    if required is None:
        raise ValueError(f"schema desconhecido: {schema_name}")

    missing = sorted(required.difference(payload.keys()))
    if missing:
        raise ValueError(
            f"payload invalido para {schema_name}; campos faltando: {', '.join(missing)}"
        )


def utc_now_iso() -> str:
    """Retorna timestamp UTC em formato ISO-8601 com sufixo Z."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )
