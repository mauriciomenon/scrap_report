import json
from pathlib import Path

import pandas as pd
import pytest

from scrap_report.cli import _emit_json, main
from scrap_report.errors import PipelineStepError
from scrap_report.secret_provider import MemorySecretProvider


def test_stage_writes_output_json(tmp_path: Path):
    source = tmp_path / "Report.xlsx"
    source.write_bytes(b"abc")
    out_json = tmp_path / "out" / "result.json"

    code = main(
        [
            "stage",
            "--source",
            str(source),
            "--staging-dir",
            str(tmp_path / "staging"),
            "--report-kind",
            "pendentes",
            "--output-json",
            str(out_json),
        ]
    )

    assert code == 0
    assert out_json.exists()
    content = out_json.read_text(encoding="utf-8")
    assert '"schema_version": "1.0.0"' in content
    assert '"generated_at": ' in content
    assert '"producer": "scrap_report.cli"' in content
    assert '"status": "ok"' in content


def test_pipeline_report_only_writes_output_json(tmp_path: Path):
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir(parents=True)
    source = staging_dir / "entrada.xlsx"
    pd.DataFrame({"Numero da SSA": ["1"]}).to_excel(source, index=False)
    out_json = tmp_path / "out" / "pipeline_report_only.json"

    code = main(
        [
            "pipeline",
            "--setor",
            "IEE3",
            "--staging-dir",
            str(staging_dir),
            "--report-kind",
            "pendentes",
            "--report-only",
            "--source-excel",
            str(source),
            "--output-json",
            str(out_json),
        ]
    )

    assert code == 0
    assert out_json.exists()
    content = out_json.read_text(encoding="utf-8")
    assert '"schema_version": "1.0.0"' in content
    assert '"generated_at": ' in content
    assert '"producer": "scrap_report.cli"' in content
    assert '"status": "ok"' in content
    assert '"reports"' in content
    assert '"telemetry"' in content


def test_pipeline_report_only_missing_source_writes_error_json(tmp_path: Path):
    out_json = tmp_path / "out" / "pipeline_error.json"

    code = main(
        [
            "pipeline",
            "--setor",
            "IEE3",
            "--staging-dir",
            str(tmp_path / "staging"),
            "--report-kind",
            "pendentes",
            "--report-only",
            "--source-excel",
            str(tmp_path / "missing.xlsx"),
            "--output-json",
            str(out_json),
        ]
    )

    assert code == 1
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["status"] == "error"
    assert payload["command"] == "pipeline"
    assert "excel nao encontrado" in payload["message"]


def test_pipeline_runtime_error_writes_redacted_error_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    def _run_pipeline(_cfg, generate_reports):
        assert generate_reports is True
        raise PipelineStepError("scrape", "falha password=leaked-value")

    monkeypatch.setattr("scrap_report.cli.run_pipeline", _run_pipeline)
    out_json = tmp_path / "out" / "pipeline_error.json"

    code = main(
        [
            "pipeline",
            "--username",
            "u1",
            "--setor",
            "IEE3",
            "--secret-service",
            "svc",
            "--output-json",
            str(out_json),
        ]
    )

    assert code == 1
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["status"] == "error"
    assert payload["command"] == "pipeline"
    assert payload["step"] == "scrape"
    assert "password=***" in payload["message"]
    assert "leaked-value" not in out_json.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("command", "runner_target"),
    [
        ("pipeline", "scrap_report.cli.run_pipeline"),
        ("ingest-latest", "scrap_report.cli.run_pipeline_from_local_download"),
    ],
)
def test_pipeline_commands_non_ok_status_return_error_code(
    command: str,
    runner_target: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    class _PipelineResult:
        status = "error"
        report_kind = "pendentes"
        source_path = tmp_path / "downloads" / "Report.xlsx"
        staged_path = tmp_path / "staging" / "Report.xlsx"
        reports = {}
        telemetry = {}

    monkeypatch.setattr(runner_target, lambda cfg, generate_reports: _PipelineResult())
    out_json = tmp_path / "out" / f"{command}.json"

    code = main(
        [
            command,
            "--username",
            "u1",
            "--setor",
            "IEE3",
            "--secret-service",
            "svc",
            "--output-json",
            str(out_json),
        ]
    )

    assert code == 1
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["status"] == "error"


def test_emit_json_fails_fast_on_invalid_payload():
    with pytest.raises(ValueError):
        _emit_json({"status": "ok"}, None, "stage_result")


def test_emit_json_blocks_sensitive_field():
    with pytest.raises(ValueError):
        _emit_json({"status": "ok", "password": "secret"}, None, "secret_result")


def test_validate_contract_command_writes_output_json(tmp_path: Path):
    out_json = tmp_path / "out" / "contract.json"
    code = main(["validate-contract", "--output-json", str(out_json)])

    assert code == 0
    assert out_json.exists()
    content = out_json.read_text(encoding="utf-8")
    assert '"schema_version": "1.0.0"' in content
    assert '"status": "ok"' in content
    assert '"contract"' in content
    assert '"package"' in content
    assert '"package_name": "scrap-report"' in content
    assert '"package_version": "0.1.17"' in content
    assert '"import_name": "scrap_report"' in content
    assert '"cli_entrypoint": "scrap-report"' in content
    assert '"module_entrypoint": "python -m scrap_report.cli"' in content
    assert '"exports"' in content
    assert '"playwright_reports"' in content
    assert '"dados": "data_xlsx"' in content
    assert '"rest_reports"' in content
    assert '"csv": "data_csv"' in content
    assert '"preferred_contracts"' in content
    assert '"sam_api_flow"' in content
    assert '"schema": "sam_api_result"' in content
    assert '"minimum_fields_by_flow"' in content
    assert '"sweep_run_rest"' in content


def test_secret_set_command_no_plaintext_leak(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    provider = MemorySecretProvider()
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    code = main(
        [
            "secret",
            "set",
            "--username",
            "u1",
            "--password",
            "super-secret",
            "--secret-service",
            "svc",
        ]
    )
    captured = capsys.readouterr().out
    assert code == 0
    assert "super-secret" not in captured
    assert '"secret_set": true' in captured


def test_secret_test_command(monkeypatch: pytest.MonkeyPatch):
    provider = MemorySecretProvider()
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)
    code = main(["secret", "test"])
    assert code == 0


def test_secret_get_command_no_plaintext_leak(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "very-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)
    code = main(["secret", "get", "--username", "u1", "--secret-service", "svc"])
    captured = capsys.readouterr().out
    assert code == 0
    assert "very-secret" not in captured
    assert '"secret_found": true' in captured


def test_secret_set_interactive_no_plaintext_leak(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)
    monkeypatch.setattr("scrap_report.cli._read_password_masked", lambda _prompt: "s3cr3t")

    code = main(
        [
            "secret",
            "set-interactive",
            "--username",
            "u1",
            "--secret-service",
            "svc",
        ]
    )
    captured = capsys.readouterr().out
    assert code == 0
    assert "s3cr3t" not in captured
    assert '"secret_set": true' in captured


def test_secret_setup_interactive_no_plaintext_leak(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)
    monkeypatch.setattr("scrap_report.cli._read_password_masked", lambda _prompt: "s3cr3t")

    code = main(
        [
            "secret",
            "setup",
            "--username",
            "u1",
            "--secret-service",
            "svc",
        ]
    )
    captured = capsys.readouterr().out
    assert code == 0
    assert "s3cr3t" not in captured
    assert '"secret_set": true' in captured
    assert '"secret_found": true' in captured


def test_scan_secrets_command_finds_issue(tmp_path: Path):
    bad = tmp_path / "bad.py"
    bad.write_text("api_key='1234567890ab'\n", encoding="utf-8")
    code = main(["scan-secrets", "--paths", str(bad)])
    assert code == 1


def test_scan_secrets_command_clean(tmp_path: Path):
    safe = tmp_path / "safe.py"
    safe.write_text("x = 1\n", encoding="utf-8")
    code = main(["scan-secrets", "--paths", str(safe)])
    assert code == 0


def test_sam_api_search_command_writes_output_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    seen = {}

    class _FakeClient:
        def __init__(self, base_url, timeout_seconds, verify_tls, ca_file=None):
            seen["base_url"] = base_url
            seen["timeout_seconds"] = timeout_seconds
            seen["verify_tls"] = verify_tls
            seen["ca_file"] = ca_file

    def fake_query(**kwargs):
        seen["query_kwargs"] = kwargs
        return (
            "search",
            [{"ssa_number": "202600001", "executor_sector": "MEL4", "detail_present": True}],
        )

    monkeypatch.setattr("scrap_report.cli.SAMApiClient", _FakeClient)
    monkeypatch.setattr("scrap_report.cli.query_sam_api_records", fake_query)

    out_json = tmp_path / "out" / "sam_api_search.json"
    code = main(
        [
            "sam-api",
            "--start-localization-code",
            "A000A000",
            "--end-localization-code",
            "Z999Z999",
            "--number-of-years",
            "7",
            "--executor-sector",
            "MEL4",
            "--executor-sector",
            "MEL3",
            "--emitter-sector",
            "IEE3",
            "--include-details",
            "--ignore-https-errors",
            "--localization-contains",
            "A0",
            "--year-week-start",
            "202609",
            "--year-week-end",
            "202610",
            "--emission-date-start",
            "2026-02-23",
            "--emission-date-end",
            "24/02/2026",
            "--limit",
            "5",
            "--output-json",
            str(out_json),
        ]
    )

    assert code == 0
    assert seen["base_url"].endswith("/SSA_API")
    assert seen["timeout_seconds"] == 30.0
    assert seen["verify_tls"] is False
    assert seen["ca_file"] is None
    assert seen["query_kwargs"]["executor_sectors"] == ("MEL4", "MEL3")
    assert seen["query_kwargs"]["emitter_sectors"] == ("IEE3",)
    assert seen["query_kwargs"]["include_details"] is True
    assert seen["query_kwargs"]["localization_contains"] == "A0"
    assert seen["query_kwargs"]["year_week_start"] == "202609"
    assert seen["query_kwargs"]["year_week_end"] == "202610"
    assert seen["query_kwargs"]["emission_date_start"] == "23/02/2026"
    assert seen["query_kwargs"]["emission_date_end"] == "24/02/2026"
    assert seen["query_kwargs"]["limit"] == 5
    content = out_json.read_text(encoding="utf-8")
    assert '"status": "ok"' in content
    assert '"count": 1' in content
    assert '"verify_tls": false' in content
    assert '"warnings": ["tls_verification_disabled"]' in content
    assert '"filters"' in content


def test_sam_api_detail_command_writes_output_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    class _FakeClient:
        def __init__(self, base_url, timeout_seconds, verify_tls, ca_file=None):
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self.verify_tls = verify_tls
            self.ca_file = ca_file

    monkeypatch.setattr("scrap_report.cli.SAMApiClient", _FakeClient)
    monkeypatch.setattr(
        "scrap_report.cli.query_sam_api_records",
        lambda **kwargs: (
            "detail",
            [{"ssa_number": "202602521", "executor_sector": "MEL4", "detail_present": True}],
        ),
    )

    out_json = tmp_path / "out" / "sam_api_detail.json"
    code = main(
        [
            "sam-api",
            "--ssa-number",
            "202602521",
            "--year-week-start",
            "202609",
            "--output-json",
            str(out_json),
        ]
    )

    assert code == 0
    content = out_json.read_text(encoding="utf-8")
    assert '"mode": "detail"' in content
    assert '"ssa_number": "202602521"' in content
    assert '"verify_tls": true' in content


def test_sam_api_detail_command_accepts_file_and_exports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    numbers_file = tmp_path / "ssas.txt"
    numbers_file.write_text("202602521\n202600001\n202602521\n", encoding="utf-8")

    class _FakeClient:
        def __init__(self, base_url, timeout_seconds, verify_tls, ca_file=None):
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self.verify_tls = verify_tls
            self.ca_file = ca_file

    seen = {}

    def fake_query(**kwargs):
        seen["kwargs"] = kwargs
        return (
            "detail",
            [
                {"ssa_number": "202602521", "executor_sector": "MEL4", "detail_present": True},
                {"ssa_number": "202600001", "executor_sector": "MAM1", "detail_present": True},
            ],
        )

    monkeypatch.setattr("scrap_report.cli.SAMApiClient", _FakeClient)
    monkeypatch.setattr("scrap_report.cli.query_sam_api_records", fake_query)

    out_json = tmp_path / "out" / "sam_api_detail_batch.json"
    out_csv = tmp_path / "out" / "sam_api_detail_batch.csv"
    out_xlsx = tmp_path / "out" / "sam_api_detail_batch.xlsx"
    code = main(
        [
            "sam-api",
            "--ssa-number-file",
            str(numbers_file),
            "--limit",
            "2",
            "--output-json",
            str(out_json),
            "--output-csv",
            str(out_csv),
            "--output-xlsx",
            str(out_xlsx),
        ]
    )

    assert code == 0
    assert seen["kwargs"]["ssa_numbers"] == ["202602521", "202600001"]
    assert out_csv.exists()
    assert out_xlsx.exists()
    content = out_json.read_text(encoding="utf-8")
    assert '"count": 2' in content
    assert '"runtime_mode": "rest"' in content
    assert '"telemetry": {' in content
    assert '"record_count": 2' in content
    assert '"detail_count": 2' in content
    assert '"without_detail_count": 0' in content
    assert '"csv": ' in content
    assert '"data_csv": ' in content
    assert '"xlsx": ' in content
    assert '"data_xlsx": ' in content
    assert '"manifest_json": ' in content
    assert '"filters"' in content
    assert '"warnings": ["ssa_numbers_deduped"]' in content


def test_sam_api_flow_panorama_writes_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    class _FakeClient:
        def __init__(self, base_url, timeout_seconds, verify_tls, ca_file=None):
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self.verify_tls = verify_tls
            self.ca_file = ca_file

    monkeypatch.setattr("scrap_report.cli.SAMApiClient", _FakeClient)
    monkeypatch.setattr(
        "scrap_report.cli.query_sam_api_records",
        lambda **kwargs: (
            "search",
            [{"ssa_number": "1", "executor_sector": "MEL4", "emitter_sector": "IEE3", "year_week": 202609, "detail_present": True}],
        ),
    )

    out_json = tmp_path / "out" / "sam_api_flow.json"
    code = main(
        [
            "sam-api-flow",
            "--profile",
            "panorama",
            "--executor-sector",
            "MEL4",
            "--output-json",
            str(out_json),
        ]
    )

    assert code == 0
    content = out_json.read_text(encoding="utf-8")
    assert '"profile": "panorama"' in content
    assert '"runtime_mode": "rest"' in content
    assert '"telemetry": {' in content
    assert '"record_count": 1' in content
    assert '"detail_count": 1' in content
    assert '"without_detail_count": 0' in content
    assert '"summary"' in content
    assert '"total": 1' in content
    assert '"manifest_json": ' in content
    assert '"verify_tls": true' in content


def test_sam_api_standalone_generates_manifest_and_exports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    class _FakeClient:
        def __init__(self, base_url, timeout_seconds, verify_tls, ca_file=None):
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self.verify_tls = verify_tls
            self.ca_file = ca_file

    monkeypatch.setattr("scrap_report.cli.SAMApiClient", _FakeClient)
    monkeypatch.setattr(
        "scrap_report.cli.query_sam_api_records",
        lambda **kwargs: (
            "detail",
            [{"ssa_number": "202602521", "executor_sector": "MEL4", "emitter_sector": "IEE3", "year_week": 202609, "detail_present": True}],
        ),
    )

    out_dir = tmp_path / "standalone"
    manifest = tmp_path / "standalone_manifest.json"
    code = main(
        [
            "sam-api-standalone",
            "--profile",
            "detail-lote",
            "--ssa-number",
            "202602521",
            "--output-dir",
            str(out_dir),
            "--output-json",
            str(manifest),
        ]
    )

    assert code == 0
    content = manifest.read_text(encoding="utf-8")
    assert '"profile": "detail-lote"' in content
    assert '"output_dir": ' in content
    assert '"runtime_mode": "rest"' in content
    assert '"telemetry": {' in content
    assert '"record_count": 1' in content
    assert '"detail_count": 1' in content
    assert '"without_detail_count": 0' in content
    assert '"csv": ' in content
    assert '"xlsx": ' in content
    assert '"summary_xlsx": ' in content
    assert '"manifest_json": ' in content
    assert '"verify_tls": true' in content
    assert '"filters"' in content


def test_sam_api_standalone_rejects_invalid_limit(tmp_path: Path):
    manifest = tmp_path / "standalone_manifest.json"

    code = main(
        [
            "sam-api-standalone",
            "--profile",
            "detail-lote",
            "--ssa-number",
            "202602521",
            "--limit",
            "0",
            "--output-json",
            str(manifest),
        ]
    )

    assert code == 1
    assert not manifest.exists()


def test_auth_flow_emits_security_notice_and_preserves_json_streams(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)
    monkeypatch.setattr("scrap_report.cli.SAMScraper", lambda cfg: type("S", (), {
        "run": lambda self: type(
            "R",
            (),
            {
                "report_kind": "pendentes",
                "downloaded_path": tmp_path / "download.xlsx",
                "started_at": "2026-03-15T00:00:00Z",
                "finished_at": "2026-03-15T00:00:01Z",
            },
        )()
    })())

    code = main(
        [
            "scrape",
            "--username",
            "u1",
            "--setor",
            "IEE3",
            "--secret-service",
            "svc",
            "--output-json",
            str(tmp_path / "scrape.json"),
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "[security]" in captured.err
    assert "secret set" in captured.err
    assert '"status": "ok"' in captured.out


def test_auth_flow_fail_closed_message_is_clean(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    code = main(
        [
            "scrape",
            "--username",
            "u1",
            "--setor",
            "IEE3",
            "--secure-required",
            "--secret-service",
            "svc",
        ]
    )
    captured = capsys.readouterr()
    assert code == 1
    assert "[error]" in captured.err
    assert "secret set" in captured.err
    assert "Traceback" not in captured.err
    assert "safe-secret" not in captured.err


def test_auth_flow_prompt_password_uses_terminal_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)
    monkeypatch.setattr("scrap_report.cli._can_prompt_for_secret", lambda: True)
    monkeypatch.setattr("scrap_report.cli._read_password_masked", lambda _prompt: "typed-secret")

    seen = {}

    class _FakeScraper:
        def __init__(self, cfg):
            seen["password"] = cfg.password

        def run(self):
            return type(
                "R",
                (),
                {
                    "report_kind": "pendentes",
                    "downloaded_path": tmp_path / "download.xlsx",
                    "started_at": "2026-03-15T00:00:00Z",
                    "finished_at": "2026-03-15T00:00:01Z",
                },
            )()

    monkeypatch.setattr("scrap_report.cli.SAMScraper", _FakeScraper)

    code = main(
        [
            "scrape",
            "--username",
            "u1",
            "--setor",
            "IEE3",
            "--allow-transitional-plaintext",
            "--prompt-password",
        ]
    )
    assert code == 0
    assert seen["password"] == "typed-secret"


def test_windows_flow_uses_existing_secret_without_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    class _PipelineResult:
        status = "ok"
        report_kind = "pendentes"
        source_path = tmp_path / "downloads" / "Report.xlsx"
        staged_path = tmp_path / "staging" / "Report.xlsx"
        reports = {"dados": "a.xlsx", "estatisticas": "b.xlsx", "relatorio_txt": "c.txt"}
        telemetry = {"pipeline_ms": 10}

    monkeypatch.setattr(
        "scrap_report.cli.run_pipeline",
        lambda cfg, generate_reports: _PipelineResult(),
    )
    monkeypatch.setattr(
        "scrap_report.cli._read_password_masked",
        lambda _prompt: pytest.fail("nao deveria pedir senha"),
    )

    code = main(
        [
            "windows-flow",
            "--username",
            "u1",
            "--setor",
            "IEE3",
            "--secret-service",
            "svc",
            "--output-json",
            str(tmp_path / "wf.json"),
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert '"status": "ok"' in captured.out


def test_windows_flow_provisions_missing_secret_interactive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)
    monkeypatch.setattr("scrap_report.cli._can_prompt_for_secret", lambda: True)
    monkeypatch.setattr("scrap_report.cli._read_password_masked", lambda _prompt: "typed-secret")

    class _PipelineResult:
        status = "ok"
        report_kind = "pendentes"
        source_path = tmp_path / "downloads" / "Report.xlsx"
        staged_path = tmp_path / "staging" / "Report.xlsx"
        reports = {"dados": "a.xlsx", "estatisticas": "b.xlsx", "relatorio_txt": "c.txt"}
        telemetry = {"pipeline_ms": 10}

    seen = {}

    def _run_pipeline(cfg, generate_reports):
        seen["password"] = cfg.password
        return _PipelineResult()

    monkeypatch.setattr("scrap_report.cli.run_pipeline", _run_pipeline)

    code = main(
        [
            "windows-flow",
            "--username",
            "u1",
            "--setor",
            "IEE3",
            "--secret-service",
            "svc",
            "--output-json",
            str(tmp_path / "wf.json"),
        ]
    )
    assert code == 0
    assert seen["password"] == "typed-secret"


def test_windows_flow_missing_secret_noninteractive_writes_error_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)
    monkeypatch.setattr("scrap_report.cli._can_prompt_for_secret", lambda: False)
    monkeypatch.setattr(
        "scrap_report.cli._read_password_masked",
        lambda _prompt: pytest.fail("nao deveria pedir senha"),
    )
    monkeypatch.setattr(
        "scrap_report.cli.run_pipeline",
        lambda _cfg, _generate_reports: pytest.fail("pipeline nao deveria rodar"),
    )
    out_json = tmp_path / "out" / "wf_error.json"

    code = main(
        [
            "windows-flow",
            "--username",
            "u1",
            "--setor",
            "IEE3",
            "--secret-service",
            "svc",
            "--output-json",
            str(out_json),
        ]
    )

    assert code == 1
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["status"] == "error"
    assert payload["command"] == "windows-flow"
    assert "terminal interativo indisponivel" in payload["message"]


def test_windows_flow_non_ok_status_returns_error_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    class _PipelineResult:
        status = "error"
        report_kind = "pendentes"
        source_path = tmp_path / "downloads" / "Report.xlsx"
        staged_path = tmp_path / "staging" / "Report.xlsx"
        reports = {}
        telemetry = {}

    monkeypatch.setattr(
        "scrap_report.cli.run_pipeline",
        lambda cfg, generate_reports: _PipelineResult(),
    )
    out_json = tmp_path / "out" / "wf_error_status.json"

    code = main(
        [
            "windows-flow",
            "--username",
            "u1",
            "--setor",
            "IEE3",
            "--secret-service",
            "svc",
            "--output-json",
            str(out_json),
        ]
    )

    assert code == 1
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["status"] == "error"


def test_windows_flow_passes_ignore_https_errors_to_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    class _PipelineResult:
        status = "ok"
        report_kind = "pendentes"
        source_path = tmp_path / "downloads" / "Report.xlsx"
        staged_path = tmp_path / "staging" / "Report.xlsx"
        reports = {"dados": "a.xlsx", "estatisticas": "b.xlsx", "relatorio_txt": "c.txt"}
        telemetry = {"pipeline_ms": 10}

    seen = {}

    def _run_pipeline(cfg, generate_reports):
        seen["ignore_https_errors"] = cfg.ignore_https_errors
        return _PipelineResult()

    monkeypatch.setattr("scrap_report.cli.run_pipeline", _run_pipeline)

    code = main(
        [
            "windows-flow",
            "--username",
            "u1",
            "--setor",
            "IEE3",
            "--secret-service",
            "svc",
            "--ignore-https-errors",
            "--output-json",
            str(tmp_path / "wf.json"),
        ]
    )

    assert code == 0
    assert seen["ignore_https_errors"] is True


def test_windows_flow_passes_setor_emissor_to_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    class _PipelineResult:
        status = "ok"
        report_kind = "pendentes"
        source_path = tmp_path / "downloads" / "Report.xlsx"
        staged_path = tmp_path / "staging" / "Report.xlsx"
        reports = {"dados": "a.xlsx", "estatisticas": "b.xlsx", "relatorio_txt": "c.txt"}
        telemetry = {"pipeline_ms": 10}

    seen = {}

    def _run_pipeline(cfg, generate_reports):
        seen["setor_emissor"] = cfg.setor_emissor
        seen["setor_executor"] = cfg.setor_executor
        return _PipelineResult()

    monkeypatch.setattr("scrap_report.cli.run_pipeline", _run_pipeline)

    code = main(
        [
            "windows-flow",
            "--username",
            "u1",
            "--setor",
            "MEL4",
            "--setor-emissor",
            "IEE3",
            "--secret-service",
            "svc",
            "--output-json",
            str(tmp_path / "wf.json"),
        ]
    )

    assert code == 0
    assert seen["setor_emissor"] == "IEE3"
    assert seen["setor_executor"] == "MEL4"


def test_windows_flow_passes_numero_ssa_to_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    class _PipelineResult:
        status = "ok"
        report_kind = "consulta_ssa"
        source_path = tmp_path / "downloads" / "Report.xlsx"
        staged_path = tmp_path / "staging" / "Report.xlsx"
        reports = {"dados": "a.xlsx", "estatisticas": "b.xlsx", "relatorio_txt": "c.txt"}
        telemetry = {"pipeline_ms": 10}

    seen = {}

    def _run_pipeline(cfg, generate_reports):
        seen["numero_ssa"] = cfg.numero_ssa
        return _PipelineResult()

    monkeypatch.setattr("scrap_report.cli.run_pipeline", _run_pipeline)

    code = main(
        [
            "windows-flow",
            "--username",
            "u1",
            "--setor",
            "ALL",
            "--setor-emissor",
            "ALL",
            "--numero-ssa",
            "202603879",
            "--report-kind",
            "consulta_ssa",
            "--secret-service",
            "svc",
            "--output-json",
            str(tmp_path / "wf_numero.json"),
        ]
    )

    assert code == 0
    assert seen["numero_ssa"] == "202603879"


def test_windows_flow_accepts_all_for_emissor_or_executor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    class _PipelineResult:
        status = "ok"
        report_kind = "pendentes"
        source_path = tmp_path / "downloads" / "Report.xlsx"
        staged_path = tmp_path / "staging" / "Report.xlsx"
        reports = {"dados": "a.xlsx", "estatisticas": "b.xlsx", "relatorio_txt": "c.txt"}
        telemetry = {"pipeline_ms": 10}

    seen = {}

    def _run_pipeline(cfg, generate_reports):
        seen["setor_emissor"] = cfg.setor_emissor
        seen["setor_executor"] = cfg.setor_executor
        return _PipelineResult()

    monkeypatch.setattr("scrap_report.cli.run_pipeline", _run_pipeline)

    code = main(
        [
            "windows-flow",
            "--username",
            "u1",
            "--setor",
            "ALL",
            "--setor-emissor",
            "ALL",
            "--secret-service",
            "svc",
            "--output-json",
            str(tmp_path / "wf_all.json"),
        ]
    )

    assert code == 0
    assert seen["setor_emissor"] is None
    assert seen["setor_executor"] is None


def test_windows_flow_accepts_pendentes_execucao_report_kind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    class _PipelineResult:
        status = "ok"
        report_kind = "pendentes_execucao"
        source_path = tmp_path / "downloads" / "Report.xlsx"
        staged_path = tmp_path / "staging" / "Report.xlsx"
        reports = {"dados": "a.xlsx", "estatisticas": "b.xlsx", "relatorio_txt": "c.txt"}
        telemetry = {"pipeline_ms": 10}

    seen = {}

    def _run_pipeline(cfg, generate_reports):
        seen["report_kind"] = cfg.report_kind
        return _PipelineResult()

    monkeypatch.setattr("scrap_report.cli.run_pipeline", _run_pipeline)

    code = main(
        [
            "windows-flow",
            "--username",
            "u1",
            "--setor",
            "MEL4",
            "--setor-emissor",
            "IEE3",
            "--report-kind",
            "pendentes_execucao",
            "--secret-service",
            "svc",
            "--output-json",
            str(tmp_path / "wf.json"),
        ]
    )

    assert code == 0
    assert seen["report_kind"] == "pendentes_execucao"


def test_windows_flow_accepts_consulta_ssa_report_kind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    class _PipelineResult:
        status = "ok"
        report_kind = "consulta_ssa"
        source_path = tmp_path / "downloads" / "Report.xlsx"
        staged_path = tmp_path / "staging" / "Report.xlsx"
        reports = {"dados": "a.xlsx", "estatisticas": "b.xlsx", "relatorio_txt": "c.txt"}
        telemetry = {"pipeline_ms": 10}

    seen = {}

    def _run_pipeline(cfg, generate_reports):
        seen["report_kind"] = cfg.report_kind
        return _PipelineResult()

    monkeypatch.setattr("scrap_report.cli.run_pipeline", _run_pipeline)

    code = main(
        [
            "windows-flow",
            "--username",
            "u1",
            "--setor",
            "MEL4",
            "--setor-emissor",
            "IEE3",
            "--report-kind",
            "consulta_ssa",
            "--secret-service",
            "svc",
            "--output-json",
            str(tmp_path / "wf.json"),
        ]
    )

    assert code == 0
    assert seen["report_kind"] == "consulta_ssa"


def test_windows_flow_accepts_consulta_ssa_print_report_kind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    class _PipelineResult:
        status = "ok"
        report_kind = "consulta_ssa_print"
        source_path = tmp_path / "downloads" / "Report.pdf"
        staged_path = tmp_path / "staging" / "Report.pdf"
        reports = {}
        telemetry = {"pipeline_ms": 10}

    seen = {}

    def _run_pipeline(cfg, generate_reports):
        seen["report_kind"] = cfg.report_kind
        return _PipelineResult()

    monkeypatch.setattr("scrap_report.cli.run_pipeline", _run_pipeline)

    code = main(
        [
            "windows-flow",
            "--username",
            "u1",
            "--setor",
            "MEL4",
            "--setor-emissor",
            "IEE3",
            "--report-kind",
            "consulta_ssa_print",
            "--secret-service",
            "svc",
            "--output-json",
            str(tmp_path / "wf.json"),
        ]
    )

    assert code == 0
    assert seen["report_kind"] == "consulta_ssa_print"


def test_windows_flow_accepts_reprogramacoes_report_kind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    class _PipelineResult:
        status = "ok"
        report_kind = "reprogramacoes"
        source_path = tmp_path / "downloads" / "Report.xlsx"
        staged_path = tmp_path / "staging" / "Report.xlsx"
        reports = {"dados": "a.xlsx", "estatisticas": "b.xlsx", "relatorio_txt": "c.txt"}
        telemetry = {"pipeline_ms": 10}

    seen = {}

    def _run_pipeline(cfg, generate_reports):
        seen["report_kind"] = cfg.report_kind
        return _PipelineResult()

    monkeypatch.setattr("scrap_report.cli.run_pipeline", _run_pipeline)

    code = main(
        [
            "windows-flow",
            "--username",
            "u1",
            "--setor",
            "MEL4",
            "--setor-emissor",
            "IEE3",
            "--report-kind",
            "reprogramacoes",
            "--secret-service",
            "svc",
            "--output-json",
            str(tmp_path / "wf.json"),
        ]
    )

    assert code == 0
    assert seen["report_kind"] == "reprogramacoes"


def test_windows_flow_accepts_aprovacao_emissao_report_kind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    class _PipelineResult:
        status = "ok"
        report_kind = "aprovacao_emissao"
        source_path = tmp_path / "downloads" / "Report.xlsx"
        staged_path = tmp_path / "staging" / "Report.xlsx"
        reports = {"dados": "a.xlsx", "estatisticas": "b.xlsx", "relatorio_txt": "c.txt"}
        telemetry = {"pipeline_ms": 10}

    seen = {}

    def _run_pipeline(cfg, generate_reports):
        seen["report_kind"] = cfg.report_kind
        return _PipelineResult()

    monkeypatch.setattr("scrap_report.cli.run_pipeline", _run_pipeline)

    code = main(
        [
            "windows-flow",
            "--username",
            "u1",
            "--setor",
            "MEL4",
            "--setor-emissor",
            "IEE3",
            "--report-kind",
            "aprovacao_emissao",
            "--secret-service",
            "svc",
            "--output-json",
            str(tmp_path / "wf.json"),
        ]
    )

    assert code == 0
    assert seen["report_kind"] == "aprovacao_emissao"


def test_windows_flow_accepts_aprovacao_cancelamento_report_kind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    class _PipelineResult:
        status = "ok"
        report_kind = "aprovacao_cancelamento"
        source_path = tmp_path / "downloads" / "Report.xlsx"
        staged_path = tmp_path / "staging" / "Report.xlsx"
        reports = {"dados": "a.xlsx", "estatisticas": "b.xlsx", "relatorio_txt": "c.txt"}
        telemetry = {"pipeline_ms": 10}

    seen = {}

    def _run_pipeline(cfg, generate_reports):
        seen["report_kind"] = cfg.report_kind
        return _PipelineResult()

    monkeypatch.setattr("scrap_report.cli.run_pipeline", _run_pipeline)

    code = main(
        [
            "windows-flow",
            "--username",
            "u1",
            "--setor",
            "MEL4",
            "--setor-emissor",
            "IEE3",
            "--report-kind",
            "aprovacao_cancelamento",
            "--secret-service",
            "svc",
            "--output-json",
            str(tmp_path / "wf.json"),
        ]
    )

    assert code == 0
    assert seen["report_kind"] == "aprovacao_cancelamento"


def test_windows_flow_accepts_derivadas_relacionadas_report_kind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    class _PipelineResult:
        status = "ok"
        report_kind = "derivadas_relacionadas"
        source_path = tmp_path / "downloads" / "Report.xlsx"
        staged_path = tmp_path / "staging" / "Report.xlsx"
        reports = {}
        telemetry = {"pipeline_ms": 10}

    seen = {}

    def _run_pipeline(cfg, generate_reports):
        seen["report_kind"] = cfg.report_kind
        return _PipelineResult()

    monkeypatch.setattr("scrap_report.cli.run_pipeline", _run_pipeline)

    code = main(
        [
            "windows-flow",
            "--username",
            "u1",
            "--setor",
            "MEL4",
            "--setor-emissor",
            "IEE3",
            "--report-kind",
            "derivadas_relacionadas",
            "--secret-service",
            "svc",
            "--output-json",
            str(tmp_path / "wf.json"),
        ]
    )

    assert code == 0
    assert seen["report_kind"] == "derivadas_relacionadas"


def test_sweep_run_writes_manifest_output_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    seen = {}

    class _Manifest:
        status = "ok"

        def to_payload(self):
            return {
                "status": "ok",
                "report_kind": "pendentes",
                "scope_mode": "executor",
                "item_count": 1,
                "success_count": 1,
                "failure_count": 0,
                "items": [
                    {
                        "index": 1,
                        "scope_mode": "executor",
                        "setor_emissor": None,
                        "setor_executor": "MEL4",
                        "status": "ok",
                        "reports": {},
                        "telemetry": {},
                    }
                ],
            }

    class _FakeRunner:
        def run(self, plan, runtime):
            seen["scope_mode"] = plan.scope_mode
            seen["setores_executor"] = plan.setores_executor
            seen["username"] = runtime.username
            return _Manifest()

    monkeypatch.setattr("scrap_report.cli.SweepRunner", lambda: _FakeRunner())

    out_json = tmp_path / "out" / "sweep.json"
    code = main(
        [
            "sweep-run",
            "--username",
            "u1",
            "--report-kind",
            "pendentes",
            "--scope-mode",
            "executor",
            "--setores-executor",
            "MEL4",
            "--secret-service",
            "svc",
            "--output-json",
            str(out_json),
        ]
    )

    assert code == 0
    assert seen["scope_mode"] == "executor"
    assert seen["setores_executor"] == ("MEL4",)
    assert seen["username"] == "u1"
    assert out_json.exists()
    content = out_json.read_text(encoding="utf-8")
    assert '"status": "ok"' in content
    assert '"item_count": 1' in content
    assert '"runtime_mode": "playwright"' in content
    assert '"manifest_json": ' in content


def test_sweep_run_returns_error_on_partial_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    class _Manifest:
        status = "partial"

        def to_payload(self):
            return {
                "status": "partial",
                "report_kind": "pendentes",
                "scope_mode": "executor",
                "item_count": 2,
                "success_count": 1,
                "failure_count": 1,
                "items": [],
            }

    class _FakeRunner:
        def run(self, plan, runtime):
            return _Manifest()

    monkeypatch.setattr("scrap_report.cli.SweepRunner", lambda: _FakeRunner())

    code = main(
        [
            "sweep-run",
            "--username",
            "u1",
            "--report-kind",
            "pendentes",
            "--scope-mode",
            "executor",
            "--setores-executor",
            "MEL4",
            "--secret-service",
            "svc",
            "--output-json",
            str(tmp_path / "out" / "sweep_partial.json"),
        ]
    )

    assert code == 1


def test_sweep_run_accepts_preset_without_scope_or_setores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    seen = {}

    class _Manifest:
        status = "ok"

        def to_payload(self):
            return {
                "status": "ok",
                "report_kind": "pendentes",
                "scope_mode": "executor",
                "item_count": 3,
                "success_count": 3,
                "failure_count": 0,
                "items": [],
            }

    class _FakeRunner:
        def run(self, plan, runtime):
            seen["scope_mode"] = plan.scope_mode
            seen["setores_executor"] = plan.setores_executor
            return _Manifest()

    monkeypatch.setattr("scrap_report.cli.SweepRunner", lambda: _FakeRunner())

    code = main(
        [
            "sweep-run",
            "--username",
            "u1",
            "--report-kind",
            "pendentes",
            "--preset",
            "principal_executor",
            "--secret-service",
            "svc",
            "--output-json",
            str(tmp_path / "out" / "sweep_preset.json"),
        ]
    )

    assert code == 0
    assert seen["scope_mode"] == "executor"
    assert seen["setores_executor"] == ("IEE3", "MEL4", "MEL3")


def test_sweep_run_accepts_runtime_rest_and_rest_tls_options(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    seen = {}

    class _Manifest:
        status = "ok"

        def to_payload(self):
            return {
                "status": "ok",
                "report_kind": "pendentes",
                "scope_mode": "executor",
                "runtime_mode": "rest",
                "item_count": 1,
                "success_count": 1,
                "failure_count": 0,
                "items": [],
            }

    class _FakeRunner:
        def run(self, plan, runtime):
            seen["runtime_mode"] = runtime.runtime_mode
            seen["rest_base_url"] = runtime.rest_base_url
            seen["rest_timeout_seconds"] = runtime.rest_timeout_seconds
            seen["rest_verify_tls"] = runtime.rest_verify_tls
            seen["rest_ca_file"] = runtime.rest_ca_file
            return _Manifest()

    monkeypatch.setattr("scrap_report.cli.SweepRunner", lambda: _FakeRunner())

    code = main(
        [
            "sweep-run",
            "--username",
            "u1",
            "--report-kind",
            "pendentes",
            "--scope-mode",
            "executor",
            "--setores-executor",
            "MEL4",
            "--runtime",
            "rest",
            "--rest-base-url",
            "https://apps.itaipu.gov.br/SAM_SMA_API/rest/SSA_API",
            "--rest-timeout-seconds",
            "45",
            "--rest-ca-file",
            str(tmp_path / "ca.pem"),
            "--secret-service",
            "svc",
            "--output-json",
            str(tmp_path / "out" / "sweep_rest.json"),
        ]
    )

    assert code == 0
    assert seen["runtime_mode"] == "rest"
    assert seen["rest_timeout_seconds"] == 45.0
    assert seen["rest_verify_tls"] is True
    assert seen["rest_ca_file"] == str(tmp_path / "ca.pem")


def test_sweep_run_rest_does_not_require_secret_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    seen = {}

    class _Manifest:
        status = "ok"

        def to_payload(self):
            return {
                "status": "ok",
                "report_kind": "pendentes",
                "scope_mode": "nenhum",
                "runtime_mode": "rest",
                "item_count": 1,
                "success_count": 1,
                "failure_count": 0,
                "items": [],
            }

    class _FakeRunner:
        def run(self, plan, runtime):
            seen["username"] = runtime.username
            seen["password"] = runtime.password
            seen["download_dir"] = runtime.download_dir
            seen["staging_dir"] = runtime.staging_dir
            return _Manifest()

    def fail_build_secret_provider():
        raise AssertionError("secret backend nao deveria ser consultado no runtime rest")

    monkeypatch.setattr("scrap_report.cli.build_secret_provider", fail_build_secret_provider)
    monkeypatch.setattr("scrap_report.cli.SweepRunner", lambda: _FakeRunner())

    code = main(
        [
            "sweep-run",
            "--report-kind",
            "pendentes",
            "--scope-mode",
            "nenhum",
            "--runtime",
            "rest",
            "--output-json",
            str(tmp_path / "out" / "sweep_rest_no_auth.json"),
        ]
    )

    assert code == 0
    assert seen["username"] == ""
    assert seen["password"] == ""
    assert seen["download_dir"] == Path("downloads")
    assert seen["staging_dir"] == Path("staging")
    content = (tmp_path / "out" / "sweep_rest_no_auth.json").read_text(encoding="utf-8")
    assert '"runtime_mode": "rest"' in content
    assert '"manifest_json": ' in content


def test_sam_api_flow_accepts_ca_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    seen = {}

    class _FakeClient:
        def __init__(self, base_url, timeout_seconds, verify_tls, ca_file=None):
            seen["verify_tls"] = verify_tls
            seen["ca_file"] = ca_file

    monkeypatch.setattr("scrap_report.cli.SAMApiClient", _FakeClient)
    monkeypatch.setattr(
        "scrap_report.cli.query_sam_api_records",
        lambda **kwargs: ("search", []),
    )

    code = main(
        [
            "sam-api-flow",
            "--profile",
            "panorama",
            "--ca-file",
            str(tmp_path / "corp-ca.pem"),
            "--output-json",
            str(tmp_path / "out" / "sam_api_flow_ca.json"),
        ]
    )

    assert code == 0
    assert seen["verify_tls"] is True
    assert seen["ca_file"] == str(tmp_path / "corp-ca.pem")


def test_sam_api_command_reports_missing_ca_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    code = main(
        [
            "sam-api",
            "--ssa-number",
            "202602521",
            "--ca-file",
            str(tmp_path / "missing-ca.pem"),
        ]
    )
    captured = capsys.readouterr()

    assert code == 1
    assert "ca_file nao encontrado" in captured.err


def test_sam_api_cert_exports_root_ca(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        "scrap_report.cli.export_server_root_ca",
        lambda **kwargs: {
            "host": kwargs["host"],
            "port": kwargs["port"],
            "output_path": kwargs["output_path"],
            "certificate_count": 2,
            "root_certificate_index": 1,
            "subject": "CN=Root",
            "issuer": "CN=Root",
            "openssl_bin": "openssl",
        },
    )

    code = main(
        [
            "sam-api-cert",
            "--output",
            str(tmp_path / "corp-root.pem"),
            "--output-json",
            str(tmp_path / "out" / "sam_api_cert.json"),
        ]
    )

    assert code == 0


def test_sweep_run_rejects_preset_with_manual_scope(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    code = main(
        [
            "sweep-run",
            "--username",
            "u1",
            "--report-kind",
            "pendentes",
            "--preset",
            "principal_executor",
            "--scope-mode",
            "executor",
            "--secret-service",
            "svc",
        ]
    )
    captured = capsys.readouterr()

    assert code == 1
    assert "preset nao pode ser combinado" in captured.err


def test_sweep_run_accepts_emission_date_manual_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    seen = {}

    class _Manifest:
        status = "ok"

        def to_payload(self):
            return {
                "status": "ok",
                "report_kind": "pendentes",
                "scope_mode": "emissor",
                "item_count": 1,
                "success_count": 1,
                "failure_count": 0,
                "items": [
                    {
                        "index": 1,
                        "scope_mode": "emissor",
                        "setor_emissor": "OUO5",
                        "setor_executor": None,
                        "emission_date_start": "25/12/2025",
                        "emission_date_end": "25/12/2025",
                        "status": "ok",
                        "reports": {},
                        "telemetry": {},
                    }
                ],
            }

    class _FakeRunner:
        def run(self, plan, runtime):
            seen["scope_mode"] = plan.scope_mode
            seen["setores_emissor"] = plan.setores_emissor
            seen["emission_date_start"] = plan.emission_date_start
            seen["emission_date_end"] = plan.emission_date_end
            return _Manifest()

    monkeypatch.setattr("scrap_report.cli.SweepRunner", lambda: _FakeRunner())

    code = main(
        [
            "sweep-run",
            "--username",
            "u1",
            "--report-kind",
            "executadas",
            "--scope-mode",
            "emissor",
            "--setores-emissor",
            "OUO5",
            "--emission-date-start",
            "2025-12-25",
            "--emission-date-end",
            "25/12/2025",
            "--secret-service",
            "svc",
            "--output-json",
            str(tmp_path / "out" / "sweep_date.json"),
        ]
    )

    assert code == 0
    assert seen["scope_mode"] == "emissor"
    assert seen["setores_emissor"] == ("OUO5",)
    assert seen["emission_date_start"] == "2025-12-25"
    assert seen["emission_date_end"] == "25/12/2025"


def test_sweep_run_accepts_numero_ssa_manual_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = MemorySecretProvider()
    provider.set_secret("svc", "u1", "safe-secret")
    monkeypatch.setattr("scrap_report.cli.build_secret_provider", lambda: provider)

    seen = {}

    class _Manifest:
        status = "ok"

        def to_payload(self):
            return {
                "status": "ok",
                "report_kind": "consulta_ssa",
                "scope_mode": "nenhum",
                "item_count": 1,
                "success_count": 1,
                "failure_count": 0,
                "items": [
                    {
                        "index": 1,
                        "scope_mode": "nenhum",
                        "setor_emissor": None,
                        "setor_executor": None,
                        "numero_ssa": "202603879",
                        "status": "ok",
                        "reports": {},
                        "telemetry": {},
                    }
                ],
            }

    class _FakeRunner:
        def run(self, plan, runtime):
            seen["scope_mode"] = plan.scope_mode
            seen["numero_ssa"] = plan.numero_ssa
            return _Manifest()

    monkeypatch.setattr("scrap_report.cli.SweepRunner", lambda: _FakeRunner())

    code = main(
        [
            "sweep-run",
            "--username",
            "u1",
            "--report-kind",
            "consulta_ssa",
            "--scope-mode",
            "nenhum",
            "--numero-ssa",
            "202603879",
            "--secret-service",
            "svc",
            "--output-json",
            str(tmp_path / "out" / "sweep_numero.json"),
        ]
    )

    assert code == 0
    assert seen["scope_mode"] == "nenhum"
    assert seen["numero_ssa"] == "202603879"
