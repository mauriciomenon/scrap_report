"""Contrato de saida JSON para integracao externa."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "1.0.0"
PRODUCER = "scrap_report.cli"

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
        "count",
        "items",
        "exports",
    },
    "sam_api_flow_result": {
        "status",
        "profile",
        "count",
        "output_dir",
        "exports",
        "summary",
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
