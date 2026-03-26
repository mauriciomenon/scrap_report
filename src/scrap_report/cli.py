"""CLI para operar pipeline de scraping e staging."""

from __future__ import annotations

import argparse
from datetime import datetime
import getpass
import json
import os
import sys
from pathlib import Path
from typing import Any

from .config import (
    CliConfigInput,
    DEFAULT_SETOR_EMISSOR,
    DEFAULT_SETOR_EXECUTOR,
    REPORT_KINDS,
    SECRET_SETUP_HINT,
    normalize_emission_date,
    report_kind_uses_excel_output,
)
from .contract import (
    PRODUCER,
    SCHEMA_VERSION,
    build_contract_catalog,
    utc_now_iso,
    validate_contract_definition,
    validate_payload_schema,
)
from .file_ops import find_latest_xlsx, stage_download
from .reporting import (
    artifacts_to_dict,
    build_sam_api_dataframe,
    export_data_csv,
    export_data_excel,
    export_sam_api_artifacts,
    generate_ssa_report_from_excel,
    sam_api_artifacts_to_dict,
)
from .redaction import assert_no_sensitive_fields
from .secret_scan import scan_paths
from .secret_provider import SecretProviderError, build_secret_provider
from .sam_api import (
    DEFAULT_SAM_API_BASE_URL,
    MAX_SAM_API_DETAIL_BATCH_SIZE,
    SAMApiClient,
    SAMApiError,
    build_sam_api_summary,
    export_server_root_ca,
    query_sam_api_records,
)

AUTH_REQUIRED_COMMANDS = {"scrape", "pipeline", "ingest-latest", "windows-flow", "sweep-run"}
SWEEP_SCOPE_CHOICES = ("emissor", "executor", "ambos", "nenhum")
SWEEP_PRESET_CHOICES = (
    "principal_emissor",
    "principal_executor",
    "principal_ambos",
    "segundo_plano_emissor",
    "segundo_plano_executor",
    "segundo_plano_ambos",
    "terceiro_plano_emissor",
    "terceiro_plano_executor",
    "terceiro_plano_ambos",
    "prioritarios_emissor",
    "prioritarios_executor",
    "prioritarios_ambos",
    "demais_emissor",
    "demais_executor",
    "demais_ambos",
)


def run_pipeline(*args: Any, **kwargs: Any) -> Any:
    from .pipeline import run_pipeline as impl

    return impl(*args, **kwargs)


def run_pipeline_from_local_download(*args: Any, **kwargs: Any) -> Any:
    from .pipeline import run_pipeline_from_local_download as impl

    return impl(*args, **kwargs)


def run_report_only(*args: Any, **kwargs: Any) -> Any:
    from .pipeline import run_report_only as impl

    return impl(*args, **kwargs)


def SAMScraper(*args: Any, **kwargs: Any) -> Any:
    from .scraper import SAMScraper as impl

    return impl(*args, **kwargs)


def _get_sweep_api() -> dict[str, Any]:
    from .sweep import (
        SWEEP_PRESET_NAMES,
        SWEEP_SCOPE_MODES,
        SweepPlan,
        SweepRunner,
        SweepRuntimeConfig,
        build_preset_plan,
    )

    return {
        "SWEEP_PRESET_NAMES": SWEEP_PRESET_NAMES,
        "SWEEP_SCOPE_MODES": SWEEP_SCOPE_MODES,
        "SweepPlan": SweepPlan,
        "SweepRunner": SweepRunner,
        "SweepRuntimeConfig": SweepRuntimeConfig,
        "build_preset_plan": build_preset_plan,
    }


def SweepPlan(*args: Any, **kwargs: Any) -> Any:
    return _get_sweep_api()["SweepPlan"](*args, **kwargs)


def SweepRunner(*args: Any, **kwargs: Any) -> Any:
    return _get_sweep_api()["SweepRunner"](*args, **kwargs)


def SweepRuntimeConfig(*args: Any, **kwargs: Any) -> Any:
    return _get_sweep_api()["SweepRuntimeConfig"](*args, **kwargs)


def build_preset_plan(*args: Any, **kwargs: Any) -> Any:
    return _get_sweep_api()["build_preset_plan"](*args, **kwargs)


def _read_password_masked(prompt: str = "password: ") -> str:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return getpass.getpass(prompt)

    if os.name == "nt":
        import msvcrt

        sys.stdout.write(prompt)
        sys.stdout.flush()
        chars: list[str] = []
        while True:
            ch = msvcrt.getwch()
            if ch in ("\r", "\n"):
                sys.stdout.write("\n")
                sys.stdout.flush()
                return "".join(chars)
            if ch == "\003":
                raise KeyboardInterrupt
            if ch == "\b":
                if chars:
                    chars.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                continue
            if ch in ("\x00", "\xe0"):
                _ = msvcrt.getwch()
                continue
            chars.append(ch)
            sys.stdout.write("*")
            sys.stdout.flush()

    import termios
    import tty

    fd = sys.stdin.fileno()
    original = termios.tcgetattr(fd)
    chars: list[str] = []
    sys.stdout.write(prompt)
    sys.stdout.flush()
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch in ("\r", "\n"):
                sys.stdout.write("\n")
                sys.stdout.flush()
                return "".join(chars)
            if ch == "\x03":
                raise KeyboardInterrupt
            if ch in ("\x7f", "\b"):
                if chars:
                    chars.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                continue
            chars.append(ch)
            sys.stdout.write("*")
            sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, original)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pipeline de scraping SAM para entrega de xlsx")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--username", default=None)
    common.add_argument("--password", default=None)
    common.add_argument(
        "--prompt-password",
        action="store_true",
        help="le senha no terminal sem eco, sem passar em linha de comando",
    )
    common.add_argument(
        "--setor",
        required=True,
        help="setor executor; use ALL para nao filtrar executor",
    )
    common.add_argument(
        "--setor-emissor",
        default=DEFAULT_SETOR_EMISSOR,
        help="setor emissor; use ALL para nao filtrar emissor",
    )
    common.add_argument("--numero-ssa", default=None, help="numero da SSA para filtro direto")
    common.add_argument("--report-kind", default="pendentes", choices=REPORT_KINDS)
    common.add_argument("--base-url", default="https://osprd.itaipu/SAM_SMA/")
    common.add_argument("--download-dir", default="downloads")
    common.add_argument("--staging-dir", default="staging")
    common.add_argument("--headed", action="store_true", help="abre browser visivel")
    common.add_argument(
        "--ignore-https-errors",
        action="store_true",
        help="ignora erros de certificado TLS no navegador",
    )
    common.add_argument("--output-json", default=None, help="salva resultado json em arquivo")
    common.add_argument(
        "--secure-required",
        action="store_true",
        help="bloqueia execucao sem backend de secret seguro",
    )
    common.add_argument(
        "--allow-transitional-plaintext",
        action="store_true",
        help="permite fallback transicional por argumento/env para senha",
    )
    common.add_argument(
        "--secret-service",
        default="scrap_report.sam",
        help="nome do servico no backend de secrets",
    )
    common.add_argument(
        "--selector-mode",
        default="adaptive",
        choices=["strict", "adaptive"],
        help="modo de resiliencia de seletor",
    )

    sub.add_parser("scrape", parents=[common], help="executa somente scraping")
    pipeline_cmd = sub.add_parser(
        "pipeline", parents=[common], help="executa scraping e gera relatorios"
    )
    pipeline_cmd.add_argument(
        "--report-only",
        action="store_true",
        help="gera relatorios a partir de xlsx ja staged, sem scraping",
    )
    pipeline_cmd.add_argument(
        "--source-excel",
        default=None,
        help="xlsx especifico para --report-only (default: mais recente em staging-dir)",
    )
    sub.add_parser(
        "ingest-latest",
        parents=[common],
        help="ingere o xlsx mais recente de downloads para staging e gera relatorios",
    )
    windows_flow = sub.add_parser(
        "windows-flow",
        help="fluxo sequencial windows: garante secret e executa pipeline seguro",
    )
    windows_flow.add_argument("--username", required=True)
    windows_flow.add_argument(
        "--setor",
        required=True,
        help="setor executor; use ALL para nao filtrar executor",
    )
    windows_flow.add_argument(
        "--setor-emissor",
        default=DEFAULT_SETOR_EMISSOR,
        help="setor emissor; use ALL para nao filtrar emissor",
    )
    windows_flow.add_argument("--numero-ssa", default=None, help="numero da SSA para filtro direto")
    windows_flow.add_argument(
        "--report-kind", default="pendentes", choices=REPORT_KINDS
    )
    windows_flow.add_argument("--base-url", default="https://osprd.itaipu/SAM_SMA/")
    windows_flow.add_argument("--download-dir", default="downloads")
    windows_flow.add_argument("--staging-dir", default="staging")
    windows_flow.add_argument("--headed", action="store_true", help="abre browser visivel")
    windows_flow.add_argument(
        "--ignore-https-errors",
        action="store_true",
        help="ignora erros de certificado TLS no navegador",
    )
    windows_flow.add_argument(
        "--secret-service",
        default="scrap_report.sam",
        help="nome do servico no backend de secrets",
    )
    windows_flow.add_argument(
        "--selector-mode",
        default="adaptive",
        choices=["strict", "adaptive"],
        help="modo de resiliencia de seletor",
    )
    windows_flow.add_argument(
        "--output-json", default=None, help="salva resultado json em arquivo"
    )
    sweep_run = sub.add_parser(
        "sweep-run",
        help="executa varredura em lote reaproveitando o pipeline atual",
    )
    sweep_run.add_argument("--username", default=None)
    sweep_run.add_argument("--password", default=None)
    sweep_run.add_argument(
        "--prompt-password",
        action="store_true",
        help="le senha no terminal sem eco, sem passar em linha de comando",
    )
    sweep_run.add_argument("--report-kind", required=True, choices=REPORT_KINDS)
    sweep_run.add_argument(
        "--preset",
        default=None,
        choices=SWEEP_PRESET_CHOICES,
        help="preset operacional de lote com janela automatica das ultimas 4 semanas",
    )
    sweep_run.add_argument(
        "--scope-mode",
        required=False,
        choices=SWEEP_SCOPE_CHOICES,
        help="define se a varredura usa emissor, executor, ambos ou nenhum filtro de setor",
    )
    sweep_run.add_argument("--setores-emissor", nargs="+", default=())
    sweep_run.add_argument("--setores-executor", nargs="+", default=())
    sweep_run.add_argument("--numero-ssa", default=None)
    sweep_run.add_argument("--year-week-start", default=None)
    sweep_run.add_argument("--year-week-end", default=None)
    sweep_run.add_argument("--emission-date-start", default=None)
    sweep_run.add_argument("--emission-date-end", default=None)
    sweep_run.add_argument("--base-url", default="https://osprd.itaipu/SAM_SMA/")
    sweep_run.add_argument("--download-dir", default="downloads")
    sweep_run.add_argument("--staging-dir", default="staging")
    sweep_run.add_argument("--headed", action="store_true", help="abre browser visivel")
    sweep_run.add_argument(
        "--ignore-https-errors",
        action="store_true",
        help="ignora erros de certificado TLS no navegador",
    )
    sweep_run.add_argument(
        "--runtime",
        default="playwright",
        choices=["playwright", "rest"],
        help="runtime do sweep: navegador oficial ou camada REST suportada",
    )
    sweep_run.add_argument(
        "--rest-base-url",
        default=DEFAULT_SAM_API_BASE_URL,
        help="base URL da SAM_SMA_API quando --runtime rest",
    )
    sweep_run.add_argument(
        "--rest-timeout-seconds",
        default=30.0,
        type=float,
        help="timeout HTTP da REST API quando --runtime rest",
    )
    sweep_run.add_argument(
        "--rest-ca-file",
        default=None,
        help="arquivo PEM opcional para validar TLS da REST API",
    )
    sweep_run.add_argument("--output-json", default=None, help="salva manifest json em arquivo")
    sweep_run.add_argument(
        "--secure-required",
        action="store_true",
        help="bloqueia execucao sem backend de secret seguro",
    )
    sweep_run.add_argument(
        "--allow-transitional-plaintext",
        action="store_true",
        help="permite fallback transicional por argumento/env para senha",
    )
    sweep_run.add_argument(
        "--secret-service",
        default="scrap_report.sam",
        help="nome do servico no backend de secrets",
    )
    sweep_run.add_argument(
        "--selector-mode",
        default="adaptive",
        choices=["strict", "adaptive"],
        help="modo de resiliencia de seletor",
    )

    stage = sub.add_parser("stage", help="move um xlsx para staging")
    stage.add_argument("--source", required=True)
    stage.add_argument("--staging-dir", default="staging")
    stage.add_argument("--report-kind", default="pendentes", choices=REPORT_KINDS)
    stage.add_argument("--output-json", default=None, help="salva resultado json em arquivo")

    report = sub.add_parser("report-from-excel", help="gera artefatos de relatorio")
    report.add_argument("--excel", required=True)
    report.add_argument("--output-dir", default="staging/reports")
    report.add_argument("--report-kind", default="pendentes", choices=REPORT_KINDS)
    report.add_argument(
        "--setor",
        default=DEFAULT_SETOR_EXECUTOR,
        help="setor executor; use ALL para nao filtrar executor",
    )
    report.add_argument(
        "--setor-emissor",
        default=DEFAULT_SETOR_EMISSOR,
        help="setor emissor; use ALL para nao filtrar emissor",
    )
    report.add_argument("--output-json", default=None, help="salva resultado json em arquivo")

    contract = sub.add_parser(
        "validate-contract", help="valida e exibe definicao do contrato json"
    )
    contract.add_argument(
        "--output-json", default=None, help="salva resultado json em arquivo"
    )
    secret = sub.add_parser("secret", help="opera secret sem expor valor")
    secret_sub = secret.add_subparsers(dest="secret_command", required=True)

    secret_set = secret_sub.add_parser("set", help="grava secret no backend seguro")
    secret_set.add_argument("--username", required=True)
    secret_set.add_argument("--password", required=True)
    secret_set.add_argument("--secret-service", default="scrap_report.sam")
    secret_setup = secret_sub.add_parser(
        "setup",
        help="fluxo simples: pede senha mascarada, grava e valida leitura",
    )
    secret_setup.add_argument("--username", required=True)
    secret_setup.add_argument("--secret-service", default="scrap_report.sam")
    secret_set_interactive = secret_sub.add_parser(
        "set-interactive",
        help="grava secret no backend seguro lendo senha sem eco",
    )
    secret_set_interactive.add_argument("--username", required=True)
    secret_set_interactive.add_argument("--secret-service", default="scrap_report.sam")

    secret_get = secret_sub.add_parser(
        "get", help="verifica existencia de secret sem exibir valor"
    )
    secret_get.add_argument("--username", required=True)
    secret_get.add_argument("--secret-service", default="scrap_report.sam")

    secret_test = secret_sub.add_parser("test", help="testa backend seguro")
    secret_test.add_argument("--secret-service", default="scrap_report.sam")
    secret_test.add_argument("--username", default=None)

    scan = sub.add_parser("scan-secrets", help="escaneia indicios locais de segredo")
    scan.add_argument(
        "--paths",
        nargs="+",
        default=["src", "tests", "README.md"],
        help="paths de entrada para scanner local",
    )
    scan.add_argument("--output-json", default=None, help="salva resultado json em arquivo")

    sam_api = sub.add_parser("sam-api", help="consulta a SAM_SMA_API sem Playwright")
    sam_api.add_argument("--base-url", default=DEFAULT_SAM_API_BASE_URL)
    sam_api.add_argument(
        "--start-localization-code",
        default="A000A000",
        help="inicio da faixa de localizacao para consulta geral",
    )
    sam_api.add_argument(
        "--end-localization-code",
        default="Z999Z999",
        help="fim da faixa de localizacao para consulta geral",
    )
    sam_api.add_argument(
        "--number-of-years",
        default=100000,
        type=int,
        help="janela de anos para consulta geral",
    )
    sam_api.add_argument(
        "--executor-sector",
        action="append",
        default=[],
        help="filtro opcional de executor; repetir para varios setores",
    )
    sam_api.add_argument(
        "--emitter-sector",
        action="append",
        default=[],
        help="filtro opcional de emissor; repetir para varios setores",
    )
    sam_api.add_argument(
        "--include-details",
        action="store_true",
        help="enriquece cada SSA com GetSSABySSANumber",
    )
    sam_api.add_argument(
        "--ssa-number",
        action="append",
        default=[],
        help="consulta detalhada por numero de SSA; repetir para varios itens",
    )
    sam_api.add_argument(
        "--ssa-number-file",
        default=None,
        help="arquivo txt com uma SSA por linha para detalhamento em lote",
    )
    sam_api.add_argument(
        "--timeout-seconds",
        default=30.0,
        type=float,
        help="timeout HTTP para a API REST",
    )
    sam_api.add_argument(
        "--localization-contains",
        default=None,
        help="substring opcional de localizacao para filtrar resultado",
    )
    sam_api.add_argument("--year-week-start", default=None)
    sam_api.add_argument("--year-week-end", default=None)
    sam_api.add_argument("--emission-date-start", default=None)
    sam_api.add_argument("--emission-date-end", default=None)
    sam_api.add_argument(
        "--limit",
        default=None,
        type=int,
        help="limite maximo de itens retornados apos filtros",
    )
    sam_api.add_argument(
        "--ignore-https-errors",
        action="store_true",
        help="ignora validacao TLS para a API REST",
    )
    sam_api.add_argument(
        "--ca-file",
        default=None,
        help="arquivo PEM opcional para validar TLS da API REST",
    )
    sam_api.add_argument("--output-csv", default=None, help="salva dados tabulares em csv")
    sam_api.add_argument("--output-xlsx", default=None, help="salva dados tabulares em xlsx")
    sam_api.add_argument("--output-json", default=None, help="salva resultado json em arquivo")

    sam_api_flow = sub.add_parser(
        "sam-api-flow",
        help="comando opinativo para uso operacional da SAM_SMA_API",
    )
    sam_api_flow.add_argument(
        "--profile",
        required=True,
        choices=["panorama", "detail-lote"],
        help="perfil operacional predefinido",
    )
    sam_api_flow.add_argument("--base-url", default=DEFAULT_SAM_API_BASE_URL)
    sam_api_flow.add_argument("--executor-sector", action="append", default=[])
    sam_api_flow.add_argument("--emitter-sector", action="append", default=[])
    sam_api_flow.add_argument("--ssa-number", action="append", default=[])
    sam_api_flow.add_argument("--ssa-number-file", default=None)
    sam_api_flow.add_argument("--start-localization-code", default="A000A000")
    sam_api_flow.add_argument("--end-localization-code", default="Z999Z999")
    sam_api_flow.add_argument("--number-of-years", default=4, type=int)
    sam_api_flow.add_argument("--localization-contains", default=None)
    sam_api_flow.add_argument("--year-week-start", default=None)
    sam_api_flow.add_argument("--year-week-end", default=None)
    sam_api_flow.add_argument("--emission-date-start", default=None)
    sam_api_flow.add_argument("--emission-date-end", default=None)
    sam_api_flow.add_argument("--limit", default=200, type=int)
    sam_api_flow.add_argument("--include-details", action="store_true")
    sam_api_flow.add_argument("--timeout-seconds", default=30.0, type=float)
    sam_api_flow.add_argument("--ignore-https-errors", action="store_true")
    sam_api_flow.add_argument("--ca-file", default=None)
    sam_api_flow.add_argument("--output-json", default=None)
    sam_api_flow.add_argument("--output-csv", default=None)
    sam_api_flow.add_argument("--output-xlsx", default=None)

    sam_api_standalone = sub.add_parser(
        "sam-api-standalone",
        help="fluxo independente da SAM_SMA_API com manifest e artefatos proprios",
    )
    sam_api_standalone.add_argument(
        "--profile",
        required=True,
        choices=["panorama", "detail-lote"],
    )
    sam_api_standalone.add_argument("--base-url", default=DEFAULT_SAM_API_BASE_URL)
    sam_api_standalone.add_argument("--executor-sector", action="append", default=[])
    sam_api_standalone.add_argument("--emitter-sector", action="append", default=[])
    sam_api_standalone.add_argument("--ssa-number", action="append", default=[])
    sam_api_standalone.add_argument("--ssa-number-file", default=None)
    sam_api_standalone.add_argument("--start-localization-code", default="A000A000")
    sam_api_standalone.add_argument("--end-localization-code", default="Z999Z999")
    sam_api_standalone.add_argument("--number-of-years", default=4, type=int)
    sam_api_standalone.add_argument("--localization-contains", default=None)
    sam_api_standalone.add_argument("--year-week-start", default=None)
    sam_api_standalone.add_argument("--year-week-end", default=None)
    sam_api_standalone.add_argument("--emission-date-start", default=None)
    sam_api_standalone.add_argument("--emission-date-end", default=None)
    sam_api_standalone.add_argument("--limit", default=200, type=int)
    sam_api_standalone.add_argument("--include-details", action="store_true")
    sam_api_standalone.add_argument("--timeout-seconds", default=30.0, type=float)
    sam_api_standalone.add_argument("--ignore-https-errors", action="store_true")
    sam_api_standalone.add_argument("--ca-file", default=None)
    sam_api_standalone.add_argument("--output-dir", default="output")
    sam_api_standalone.add_argument("--output-json", default=None)

    sam_api_cert = sub.add_parser(
        "sam-api-cert",
        help="exporta a CA raiz apresentada pelo host REST para uso com --ca-file",
    )
    sam_api_cert.add_argument("--host", default="apps.itaipu.gov.br")
    sam_api_cert.add_argument("--port", default=443, type=int)
    sam_api_cert.add_argument("--output", required=True)
    sam_api_cert.add_argument("--openssl-bin", default=None)
    sam_api_cert.add_argument("--timeout-seconds", default=30.0, type=float)
    sam_api_cert.add_argument("--output-json", default=None)

    return parser


def _emit_json(
    payload: dict[str, Any], output_json: str | None, schema_name: str
) -> None:
    assert_no_sensitive_fields(payload)
    validate_payload_schema(schema_name, payload)
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "producer": PRODUCER,
        **payload,
    }
    text = json.dumps(normalized, ensure_ascii=True)
    print(text)
    if output_json:
        out = Path(output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")


def _emit_unvalidated_json(payload: dict[str, Any], output_json: str | None) -> None:
    assert_no_sensitive_fields(payload)
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "producer": PRODUCER,
        **payload,
    }
    text = json.dumps(normalized, ensure_ascii=True)
    print(text)
    if output_json:
        out = Path(output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")


def _read_ssa_numbers_from_file(path_value: str | None) -> list[str]:
    if not path_value:
        return []
    path = Path(path_value)
    content = path.read_text(encoding="utf-8")
    return [line.strip() for line in content.splitlines() if line.strip()]


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    unique_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_values.append(normalized)
    return unique_values


def _normalize_optional_path(path_value: str | None) -> str | None:
    if not path_value:
        return None
    return str(Path(path_value).expanduser().resolve())


def _normalize_optional_emission_date_window(
    emission_date_start: str | None,
    emission_date_end: str | None,
) -> tuple[str | None, str | None]:
    normalized_start = normalize_emission_date(emission_date_start)
    normalized_end = normalize_emission_date(emission_date_end)
    if bool(normalized_start) != bool(normalized_end):
        raise ValueError("filtro por data de emissao exige inicio e fim")
    return normalized_start or None, normalized_end or None


def _export_sam_api_records(
    records: list[dict[str, Any]],
    output_csv: str | None,
    output_xlsx: str | None,
) -> dict[str, str]:
    exports: dict[str, str] = {}
    if not output_csv and not output_xlsx:
        return exports
    df = build_sam_api_dataframe(records)
    if output_csv:
        csv_path = str(export_data_csv(df, Path(output_csv)))
        exports["csv"] = csv_path
        exports["data_csv"] = csv_path
    if output_xlsx:
        xlsx_path = str(export_data_excel(df, Path(output_xlsx)))
        exports["xlsx"] = xlsx_path
        exports["data_xlsx"] = xlsx_path
    return exports


def _resolve_sam_api_ssa_numbers(args: Any) -> list[str]:
    return _dedupe_preserve_order(args.ssa_number + _read_ssa_numbers_from_file(args.ssa_number_file))


def _validate_sam_api_limit(limit: int | None) -> None:
    if limit is not None and limit <= 0:
        raise ValueError("limit deve ser maior que zero")


def _build_sam_api_filters(args: Any, mode: str) -> dict[str, Any]:
    normalized_emission_start, normalized_emission_end = _normalize_optional_emission_date_window(
        args.emission_date_start,
        args.emission_date_end,
    )
    filters: dict[str, Any] = {
        "executor_sectors": list(args.executor_sector),
        "emitter_sectors": list(args.emitter_sector),
        "localization_contains": args.localization_contains,
        "year_week_start": args.year_week_start,
        "year_week_end": args.year_week_end,
        "emission_date_start": normalized_emission_start,
        "emission_date_end": normalized_emission_end,
        "limit": args.limit,
    }
    if mode == "detail":
        filters["ssa_numbers"] = _resolve_sam_api_ssa_numbers(args)
    else:
        filters["start_localization_code"] = args.start_localization_code
        filters["end_localization_code"] = args.end_localization_code
        filters["number_of_years"] = args.number_of_years
        filters["include_details"] = bool(getattr(args, "include_details", False))
    return filters


def _build_sam_api_warnings(args: Any) -> list[str]:
    warnings: list[str] = []
    if args.ignore_https_errors:
        warnings.append("tls_verification_disabled")
    if getattr(args, "ca_file", None):
        warnings.append("custom_ca_file_configured")
    raw_ssa_numbers = args.ssa_number + _read_ssa_numbers_from_file(args.ssa_number_file)
    ssa_numbers = _resolve_sam_api_ssa_numbers(args)
    if len(raw_ssa_numbers) != len(ssa_numbers):
        warnings.append("ssa_numbers_deduped")
    if len(ssa_numbers) > MAX_SAM_API_DETAIL_BATCH_SIZE:
        warnings.append("detail_batch_chunked")
    return warnings


def _run_sam_api_query(args: Any, client: SAMApiClient) -> tuple[str, list[dict[str, Any]]]:
    normalized_emission_start, normalized_emission_end = _normalize_optional_emission_date_window(
        args.emission_date_start,
        args.emission_date_end,
    )
    _validate_sam_api_limit(args.limit)
    ssa_numbers = _resolve_sam_api_ssa_numbers(args)
    include_details = bool(getattr(args, "include_details", False))
    if getattr(args, "profile", None) == "detail-lote":
        include_details = True
        if not ssa_numbers:
            raise ValueError("profile detail-lote exige --ssa-number ou --ssa-number-file")
    if getattr(args, "profile", None) == "panorama" and not ssa_numbers:
        include_details = bool(include_details or args.year_week_start or args.year_week_end or args.emission_date_start or args.emission_date_end)
    return query_sam_api_records(
        client=client,
        ssa_numbers=ssa_numbers,
        executor_sectors=tuple(args.executor_sector),
        emitter_sectors=tuple(args.emitter_sector),
        start_localization_code=args.start_localization_code,
        end_localization_code=args.end_localization_code,
        number_of_years=args.number_of_years,
        include_details=include_details,
        localization_contains=args.localization_contains,
        year_week_start=args.year_week_start,
        year_week_end=args.year_week_end,
        emission_date_start=normalized_emission_start,
        emission_date_end=normalized_emission_end,
        limit=args.limit,
    )


def _build_sam_api_payload(mode: str, items: list[dict[str, Any]], args: Any) -> dict[str, Any]:
    summary = build_sam_api_summary(items)
    payload: dict[str, Any] = {
        "status": "ok",
        "mode": mode,
        "runtime_mode": "rest",
        "count": len(items),
        "items": items,
        "telemetry": {
            "record_count": summary["total"],
            "detail_count": summary["detail_count"],
            "without_detail_count": summary["without_detail_count"],
        },
        "exports": {},
        "manifest_json": None,
        "filters": _build_sam_api_filters(args, mode),
        "warnings": _build_sam_api_warnings(args),
        "verify_tls": not args.ignore_https_errors,
        "timeout_seconds": args.timeout_seconds,
    }
    if mode == "detail":
        payload["ssa_numbers"] = _resolve_sam_api_ssa_numbers(args)
    else:
        payload["executor_sectors"] = args.executor_sector
        payload["emitter_sectors"] = args.emitter_sector
        payload["include_details"] = bool(getattr(args, "include_details", False))
        payload["start_localization_code"] = args.start_localization_code
        payload["end_localization_code"] = args.end_localization_code
        payload["number_of_years"] = args.number_of_years
        payload["localization_contains"] = args.localization_contains
    return payload


def _build_default_sam_api_output_dir(profile: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("output") / f"sam_api_{profile}_{stamp}"


def _build_default_sam_api_manifest_path(output_dir: Path, profile: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return output_dir / f"sam_api_manifest_{profile}_{stamp}.json"


def _build_sam_api_flow_payload(
    profile: str,
    mode: str,
    args: Any,
    output_dir: Path,
    items: list[dict[str, Any]],
    exports: dict[str, str],
) -> dict[str, Any]:
    summary = build_sam_api_summary(items)
    return {
        "status": "ok",
        "profile": profile,
        "mode": mode,
        "runtime_mode": "rest",
        "count": len(items),
        "output_dir": str(output_dir),
        "telemetry": {
            "record_count": summary["total"],
            "detail_count": summary["detail_count"],
            "without_detail_count": summary["without_detail_count"],
        },
        "exports": exports,
        "manifest_json": None,
        "summary": summary,
        "filters": _build_sam_api_filters(args, mode),
        "warnings": _build_sam_api_warnings(args),
        "verify_tls": not args.ignore_https_errors,
        "timeout_seconds": args.timeout_seconds,
    }


def _build_default_sweep_output_json(staging_dir: Path, report_kind: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return staging_dir / f"sweep_{report_kind}_{stamp}.json"


def _print_secret_policy_notice(args: Any, output_json: str | None) -> None:
    if not _command_requires_auth(args):
        return
    notice = (
        "[security] Esta etapa resolve credencial de login antes da operacao. "
        "Ordem: argumento --password, depois secret store do OS, e por ultimo "
        "SAM_PASSWORD apenas em modo transicional permitido. "
        "Politica: fail-closed quando secure-required estiver ativo ou "
        "plaintext transicional estiver desabilitado. "
        + SECRET_SETUP_HINT
    )
    print(notice, file=sys.stderr)
    if output_json:
        print(
            "[security] Aviso emitido em stderr para preservar JSON limpo em stdout.",
            file=sys.stderr,
        )


def _command_requires_auth(args: Any) -> bool:
    if args.command != "sweep-run":
        return args.command in AUTH_REQUIRED_COMMANDS
    return getattr(args, "runtime", "playwright") != "rest"


def _ensure_secret_available(
    provider: Any, secret_service: str, username: str
) -> bool:
    try:
        provider.get_secret(secret_service, username)
        return True
    except SecretProviderError:
        password = _read_password_masked("password (secret ausente): ")
        try:
            provider.set_secret(secret_service, username, password)
        except SecretProviderError as exc:
            print(f"[error] falha ao gravar secret: {exc}", file=sys.stderr)
            return False
        return True


def main(argv: list[str] | None = None) -> int:
    validate_contract_definition()

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate-contract":
        _emit_json(
            {
                "status": "ok",
                "contract": build_contract_catalog(),
            },
            args.output_json,
            "contract_info",
        )
        return 0

    if args.command == "secret":
        provider = build_secret_provider()
        if args.secret_command == "test":
            ok = provider.test_backend()
            _emit_json(
                {"status": "ok" if ok else "error", "backend_ready": ok},
                None,
                "secret_result",
            )
            return 0 if ok else 1
        if args.secret_command == "set":
            try:
                provider.set_secret(args.secret_service, args.username, args.password)
            except SecretProviderError as exc:
                _emit_json(
                    {"status": "error", "message": str(exc)},
                    None,
                    "secret_result",
                )
                return 1
            _emit_json(
                {"status": "ok", "secret_set": True, "username": args.username},
                None,
                "secret_result",
            )
            return 0
        if args.secret_command == "setup":
            password = _read_password_masked("password: ")
            try:
                provider.set_secret(args.secret_service, args.username, password)
                provider.get_secret(args.secret_service, args.username)
            except SecretProviderError as exc:
                _emit_json(
                    {"status": "error", "message": str(exc)},
                    None,
                    "secret_result",
                )
                return 1
            _emit_json(
                {
                    "status": "ok",
                    "secret_set": True,
                    "secret_found": True,
                    "username": args.username,
                },
                None,
                "secret_result",
            )
            return 0
        if args.secret_command == "set-interactive":
            password = _read_password_masked("password: ")
            try:
                provider.set_secret(args.secret_service, args.username, password)
            except SecretProviderError as exc:
                _emit_json(
                    {"status": "error", "message": str(exc)},
                    None,
                    "secret_result",
                )
                return 1
            _emit_json(
                {"status": "ok", "secret_set": True, "username": args.username},
                None,
                "secret_result",
            )
            return 0
        if args.secret_command == "get":
            try:
                provider.get_secret(args.secret_service, args.username)
            except SecretProviderError:
                _emit_json(
                    {"status": "error", "secret_found": False, "username": args.username},
                    None,
                    "secret_result",
                )
                return 1
            _emit_json(
                {"status": "ok", "secret_found": True, "username": args.username},
                None,
                "secret_result",
            )
            return 0

    if args.command == "scan-secrets":
        findings = scan_paths([Path(item) for item in args.paths])
        payload = {
            "status": "ok" if not findings else "error",
            "findings_count": len(findings),
            "findings": [
                {
                    "path": f.path,
                    "line": f.line,
                    "rule": f.rule,
                    "excerpt": f.excerpt,
                }
                for f in findings
            ],
        }
        _emit_json(payload, args.output_json, "scan_result")
        return 0 if not findings else 1

    if args.command == "sam-api":
        client = SAMApiClient(
            base_url=args.base_url,
            timeout_seconds=args.timeout_seconds,
            verify_tls=not args.ignore_https_errors,
            ca_file=_normalize_optional_path(args.ca_file),
        )
        try:
            mode, items = _run_sam_api_query(args, client)
            payload = _build_sam_api_payload(mode, items, args)
        except (ValueError, SAMApiError) as exc:
            print(f"[error] {exc}", file=sys.stderr)
            return 1
        payload["exports"] = _export_sam_api_records(
            records=payload["items"],
            output_csv=args.output_csv,
            output_xlsx=args.output_xlsx,
        )
        if args.output_json:
            payload["manifest_json"] = str(Path(args.output_json))
            payload["exports"]["manifest_json"] = payload["manifest_json"]
        _emit_json(payload, args.output_json, "sam_api_result")
        return 0

    if args.command == "sam-api-flow":
        client = SAMApiClient(
            base_url=args.base_url,
            timeout_seconds=args.timeout_seconds,
            verify_tls=not args.ignore_https_errors,
            ca_file=_normalize_optional_path(args.ca_file),
        )
        try:
            mode, items = _run_sam_api_query(args, client)
            payload = _build_sam_api_payload(mode, items, args)
        except (ValueError, SAMApiError) as exc:
            print(f"[error] {exc}", file=sys.stderr)
            return 1
        payload["profile"] = args.profile
        payload["summary"] = build_sam_api_summary(items)
        payload["exports"] = _export_sam_api_records(
            records=items,
            output_csv=args.output_csv,
            output_xlsx=args.output_xlsx,
        )
        if args.output_json:
            payload["manifest_json"] = str(Path(args.output_json))
            payload["exports"]["manifest_json"] = payload["manifest_json"]
        _emit_json(payload, args.output_json, "sam_api_result")
        return 0

    if args.command == "sam-api-standalone":
        client = SAMApiClient(
            base_url=args.base_url,
            timeout_seconds=args.timeout_seconds,
            verify_tls=not args.ignore_https_errors,
            ca_file=_normalize_optional_path(args.ca_file),
        )
        try:
            _validate_sam_api_limit(args.limit)
            mode, items = _run_sam_api_query(args, client)
            output_dir = Path(args.output_dir) if args.output_dir else _build_default_sam_api_output_dir(args.profile)
            artifacts = export_sam_api_artifacts(items, output_dir, f"sam_api_{args.profile}")
            payload = _build_sam_api_flow_payload(
                profile=args.profile,
                mode=mode,
                args=args,
                output_dir=output_dir,
                items=items,
                exports=sam_api_artifacts_to_dict(artifacts),
            )
        except (ValueError, SAMApiError) as exc:
            print(f"[error] {exc}", file=sys.stderr)
            return 1
        manifest_path = args.output_json or str(_build_default_sam_api_manifest_path(output_dir, args.profile))
        payload["manifest_json"] = manifest_path
        payload["exports"]["manifest_json"] = manifest_path
        _emit_json(payload, manifest_path, "sam_api_flow_result")
        return 0

    if args.command == "sam-api-cert":
        try:
            payload = {
                "status": "ok",
                **export_server_root_ca(
                    output_path=args.output,
                    host=args.host,
                    port=args.port,
                    openssl_bin=args.openssl_bin,
                    timeout_seconds=args.timeout_seconds,
                ),
            }
        except SAMApiError as exc:
            print(f"[error] {exc}", file=sys.stderr)
            return 1
        _emit_unvalidated_json(payload, args.output_json)
        return 0

    if args.command == "windows-flow":
        _print_secret_policy_notice(args, args.output_json)
        provider = build_secret_provider()
        if not provider.test_backend():
            print("[error] backend de secret indisponivel", file=sys.stderr)
            return 1
        if not _ensure_secret_available(provider, args.secret_service, args.username):
            return 1
        try:
            cfg = CliConfigInput(
                username=args.username,
                password=None,
                setor_emissor=args.setor_emissor,
                setor_executor=args.setor,
                report_kind=args.report_kind,
                base_url=args.base_url,
                headless=not args.headed,
                download_dir=args.download_dir,
                staging_dir=args.staging_dir,
                secure_required=True,
                allow_transitional_plaintext=False,
                secret_service=args.secret_service,
                secret_provider=provider,
                selector_mode=args.selector_mode,
                ignore_https_errors=args.ignore_https_errors,
                numero_ssa=args.numero_ssa,
            ).to_scrape_config()
        except ValueError as exc:
            print(f"[error] {exc}", file=sys.stderr)
            return 1
        pipeline_result = run_pipeline(cfg, generate_reports=True)
        _emit_json(
            {
                "status": pipeline_result.status,
                "report_kind": pipeline_result.report_kind,
                "source_path": str(pipeline_result.source_path),
                "staged_path": str(pipeline_result.staged_path),
                "reports": pipeline_result.reports,
                "telemetry": pipeline_result.telemetry,
            },
            args.output_json,
            "pipeline_result",
        )
        return 0

    if args.command == "sweep-run":
        _print_secret_policy_notice(args, args.output_json)
        input_password = args.password
        if args.runtime != "rest" and args.prompt_password and not input_password:
            input_password = _read_password_masked("password: ")
        try:
            if args.preset:
                conflict_values = [
                    args.scope_mode,
                    bool(args.setores_emissor),
                    bool(args.setores_executor),
                    args.year_week_start,
                    args.year_week_end,
                    args.emission_date_start,
                    args.emission_date_end,
                ]
                if any(conflict_values):
                    raise ValueError(
                        "preset nao pode ser combinado com scope-mode, setores ou filtros de data manuais"
                    )
            if args.preset:
                plan = build_preset_plan(args.preset, args.report_kind)
            else:
                if not args.scope_mode:
                    raise ValueError("scope-mode obrigatorio quando preset nao for informado")
                plan = SweepPlan(
                    report_kind=args.report_kind,
                    scope_mode=args.scope_mode,
                    setores_emissor=tuple(args.setores_emissor),
                    setores_executor=tuple(args.setores_executor),
                    numero_ssa=args.numero_ssa,
                    emission_year_week_start=args.year_week_start,
                    emission_year_week_end=args.year_week_end,
                    emission_date_start=args.emission_date_start,
                    emission_date_end=args.emission_date_end,
                )
            if args.runtime == "rest":
                download_dir = Path(args.download_dir)
                staging_dir = Path(args.staging_dir)
                download_dir.mkdir(parents=True, exist_ok=True)
                staging_dir.mkdir(parents=True, exist_ok=True)
                runtime = SweepRuntimeConfig(
                    username=(args.username or "").strip(),
                    password=(input_password or "").strip(),
                    base_url=args.base_url,
                    headless=not args.headed,
                    download_dir=download_dir,
                    staging_dir=staging_dir,
                    selector_mode=args.selector_mode,
                    ignore_https_errors=args.ignore_https_errors,
                    generate_reports=True,
                    runtime_mode=args.runtime,
                    rest_base_url=args.rest_base_url,
                    rest_timeout_seconds=args.rest_timeout_seconds,
                    rest_verify_tls=not args.ignore_https_errors,
                    rest_ca_file=_normalize_optional_path(args.rest_ca_file),
                )
                manifest = SweepRunner().run(plan, runtime)
                output_json = args.output_json or str(
                    _build_default_sweep_output_json(staging_dir, args.report_kind)
                )
                payload = manifest.to_payload()
                payload.setdefault("runtime_mode", args.runtime)
                payload["manifest_json"] = output_json
                _emit_json(payload, output_json, "sweep_result")
                return 0 if manifest.status == "ok" else 1
            base_cfg = CliConfigInput(
                username=args.username,
                password=input_password,
                setor_emissor="ALL",
                setor_executor="ALL",
                report_kind=args.report_kind,
                base_url=args.base_url,
                headless=not args.headed,
                download_dir=args.download_dir,
                staging_dir=args.staging_dir,
                secure_required=args.secure_required,
                allow_transitional_plaintext=args.allow_transitional_plaintext,
                secret_service=args.secret_service,
                secret_provider=build_secret_provider(),
                selector_mode=args.selector_mode,
                ignore_https_errors=args.ignore_https_errors,
            ).to_scrape_config()
        except ValueError as exc:
            print(f"[error] {exc}", file=sys.stderr)
            return 1

        runtime = SweepRuntimeConfig(
            username=base_cfg.username,
            password=base_cfg.password,
            base_url=base_cfg.base_url,
            headless=base_cfg.headless,
            download_dir=base_cfg.download_dir,
            staging_dir=base_cfg.staging_dir,
            selector_mode=base_cfg.selector_mode,
            ignore_https_errors=base_cfg.ignore_https_errors,
            generate_reports=True,
            runtime_mode=args.runtime,
            rest_base_url=args.rest_base_url,
            rest_timeout_seconds=args.rest_timeout_seconds,
            rest_verify_tls=not args.ignore_https_errors,
            rest_ca_file=_normalize_optional_path(args.rest_ca_file),
        )
        manifest = SweepRunner().run(plan, runtime)
        output_json = args.output_json or str(
            _build_default_sweep_output_json(base_cfg.staging_dir, args.report_kind)
        )
        payload = manifest.to_payload()
        payload.setdefault("runtime_mode", args.runtime)
        payload["manifest_json"] = output_json
        _emit_json(payload, output_json, "sweep_result")
        return 0 if manifest.status == "ok" else 1

    if args.command == "pipeline" and args.report_only:
        if not report_kind_uses_excel_output(args.report_kind):
            print(
                "[error] report_only indisponivel para report_kind sem excel",
                file=sys.stderr,
            )
            return 1
        source_excel = (
            Path(args.source_excel)
            if args.source_excel
            else find_latest_xlsx(Path(args.staging_dir))
        )
        pipeline_result = run_report_only(
            source_excel=source_excel,
            report_kind=args.report_kind,
            reports_output_dir=Path(args.staging_dir) / "reports",
            setor_emissor=args.setor_emissor,
            setor_executor=args.setor,
        )
        _emit_json(
            {
                "status": pipeline_result.status,
                "report_kind": pipeline_result.report_kind,
                "source_path": str(pipeline_result.source_path),
                "staged_path": str(pipeline_result.staged_path),
                "reports": pipeline_result.reports,
                "telemetry": pipeline_result.telemetry,
            },
            args.output_json,
            "pipeline_result",
        )
        return 0

    if args.command in {"scrape", "pipeline", "ingest-latest"}:
        _print_secret_policy_notice(args, args.output_json)
        input_password = args.password
        if args.prompt_password and not input_password:
            input_password = _read_password_masked("password: ")
        try:
            cfg = CliConfigInput(
                username=args.username,
                password=input_password,
                setor_emissor=args.setor_emissor,
                setor_executor=args.setor,
                report_kind=args.report_kind,
                base_url=args.base_url,
                headless=not args.headed,
                download_dir=args.download_dir,
                staging_dir=args.staging_dir,
                secure_required=args.secure_required,
                allow_transitional_plaintext=args.allow_transitional_plaintext,
                secret_service=args.secret_service,
                secret_provider=build_secret_provider(),
                selector_mode=args.selector_mode,
                ignore_https_errors=args.ignore_https_errors,
                numero_ssa=args.numero_ssa,
            ).to_scrape_config()
        except ValueError as exc:
            print(f"[error] {exc}", file=sys.stderr)
            return 1

        if args.command == "scrape":
            result = SAMScraper(cfg).run()
            _emit_json(
                {
                    "status": "ok",
                    "report_kind": result.report_kind,
                    "downloaded_path": str(result.downloaded_path),
                    "started_at": result.started_at,
                    "finished_at": result.finished_at,
                },
                args.output_json,
                "scrape_result",
            )
            return 0

        if args.command == "pipeline":
            pipeline_result = run_pipeline(cfg, generate_reports=True)
        else:
            pipeline_result = run_pipeline_from_local_download(
                cfg, generate_reports=True
            )
        _emit_json(
            {
                "status": pipeline_result.status,
                "report_kind": pipeline_result.report_kind,
                "source_path": str(pipeline_result.source_path),
                "staged_path": str(pipeline_result.staged_path),
                "reports": pipeline_result.reports,
                "telemetry": pipeline_result.telemetry,
            },
            args.output_json,
            "pipeline_result",
        )
        return 0

    if args.command == "stage":
        staged = stage_download(
            source_path=Path(args.source),
            staging_dir=Path(args.staging_dir),
            report_kind=args.report_kind,
            overwrite=False,
        )
        _emit_json(
            {"status": "ok", "staged_path": str(staged)},
            args.output_json,
            "stage_result",
        )
        return 0

    if args.command == "report-from-excel":
        artifacts = generate_ssa_report_from_excel(
            Path(args.excel),
            Path(args.output_dir),
            report_kind=args.report_kind,
            setor_emissor=args.setor_emissor,
            setor_executor=args.setor,
        )
        _emit_json(
            {"status": "ok", "reports": artifacts_to_dict(artifacts)},
            args.output_json,
            "report_result",
        )
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
