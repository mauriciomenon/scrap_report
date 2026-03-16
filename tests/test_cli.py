from pathlib import Path

import pandas as pd
import pytest

from scrap_report.cli import _emit_json, main
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


def test_scan_secrets_command_finds_issue(tmp_path: Path):
    bad = tmp_path / "bad.py"
    bad.write_text("api_key='123'\n", encoding="utf-8")
    code = main(["scan-secrets", "--paths", str(bad)])
    assert code == 1


def test_scan_secrets_command_clean(tmp_path: Path):
    safe = tmp_path / "safe.py"
    safe.write_text("x = 1\n", encoding="utf-8")
    code = main(["scan-secrets", "--paths", str(safe)])
    assert code == 0


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

    monkeypatch.setattr("scrap_report.cli.run_pipeline", lambda cfg, generate_reports: _PipelineResult())
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
