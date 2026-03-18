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
    report_kind_uses_excel_output,
)
from .contract import (
    PRODUCER,
    SCHEMA_REQUIRED_FIELDS,
    SCHEMA_VERSION,
    utc_now_iso,
    validate_contract_definition,
    validate_payload_schema,
)
from .file_ops import find_latest_xlsx, stage_download
from .pipeline import run_pipeline, run_pipeline_from_local_download, run_report_only
from .reporting import artifacts_to_dict, generate_ssa_report_from_excel
from .redaction import assert_no_sensitive_fields
from .scraper import SAMScraper
from .secret_scan import scan_paths
from .secret_provider import SecretProviderError, build_secret_provider
from .sweep import (
    SWEEP_PRESET_NAMES,
    SWEEP_SCOPE_MODES,
    SweepPlan,
    SweepRunner,
    SweepRuntimeConfig,
    build_preset_plan,
)

AUTH_REQUIRED_COMMANDS = {"scrape", "pipeline", "ingest-latest", "windows-flow", "sweep-run"}


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
        choices=SWEEP_PRESET_NAMES,
        help="preset operacional de lote com janela automatica das ultimas 4 semanas",
    )
    sweep_run.add_argument(
        "--scope-mode",
        required=False,
        choices=SWEEP_SCOPE_MODES,
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


def _build_default_sweep_output_json(staging_dir: Path, report_kind: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return staging_dir / f"sweep_{report_kind}_{stamp}.json"


def _print_secret_policy_notice(command: str, output_json: str | None) -> None:
    if command not in AUTH_REQUIRED_COMMANDS:
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
                "contract": {
                    "schema_version": SCHEMA_VERSION,
                    "producer": PRODUCER,
                    "schemas": {
                        name: sorted(fields)
                        for name, fields in SCHEMA_REQUIRED_FIELDS.items()
                    },
                },
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

    if args.command == "windows-flow":
        _print_secret_policy_notice(args.command, args.output_json)
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
        _print_secret_policy_notice(args.command, args.output_json)
        input_password = args.password
        if args.prompt_password and not input_password:
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
        )
        manifest = SweepRunner().run(plan, runtime)
        output_json = args.output_json or str(
            _build_default_sweep_output_json(base_cfg.staging_dir, args.report_kind)
        )
        _emit_unvalidated_json(manifest.to_payload(), output_json)
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
        _print_secret_policy_notice(args.command, args.output_json)
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
