from pathlib import Path

import pandas as pd
import pytest

from scrap_report.config import ScrapeConfig
from scrap_report.errors import PipelineStepError
from scrap_report.pipeline import (
    run_pipeline,
    run_pipeline_from_local_download,
    run_report_only,
)
from scrap_report.scraper import ScrapeResult


def test_run_pipeline_offline_with_mock_scraper(monkeypatch, tmp_path: Path):
    download_dir = tmp_path / "downloads"
    stage_dir = tmp_path / "staging"
    download_dir.mkdir()

    downloaded = download_dir / "Report.xlsx"
    pd.DataFrame({"Numero da SSA": ["1"]}).to_excel(downloaded, index=False)

    def fake_run(self):
        return ScrapeResult(
            report_kind="pendentes",
            downloaded_path=downloaded,
            started_at="2026-03-15T10:00:00",
            finished_at="2026-03-15T10:00:10",
        )

    monkeypatch.setattr("scrap_report.pipeline.SAMScraper.run", fake_run)

    cfg = ScrapeConfig(
        username="u",
        password="p",
        setor_executor="IEE3",
        report_kind="pendentes",
        download_dir=download_dir,
        staging_dir=stage_dir,
    )

    result = run_pipeline(cfg, generate_reports=True)

    assert result.status == "ok"
    assert result.staged_path.exists()
    assert "dados" in result.reports
    assert Path(result.reports["dados"]).exists()
    assert "scrape_ms" in result.telemetry
    assert "stage_ms" in result.telemetry
    assert "report_ms" in result.telemetry


def test_run_pipeline_from_local_download(tmp_path: Path):
    download_dir = tmp_path / "downloads"
    stage_dir = tmp_path / "staging"
    download_dir.mkdir()

    downloaded = download_dir / "Report.xlsx"
    pd.DataFrame({"Numero da SSA": ["1", "2"]}).to_excel(downloaded, index=False)

    cfg = ScrapeConfig(
        username="u",
        password="p",
        setor_executor="IEE3",
        report_kind="pendentes",
        download_dir=download_dir,
        staging_dir=stage_dir,
    )

    result = run_pipeline_from_local_download(cfg, generate_reports=True)

    assert result.status == "ok"
    assert result.source_path == downloaded
    assert result.staged_path.exists()
    assert "dados" in result.reports
    assert "find_download_ms" in result.telemetry
    assert "stage_ms" in result.telemetry
    assert "report_ms" in result.telemetry


def test_run_pipeline_offline_pdf_skips_reports(monkeypatch, tmp_path: Path):
    download_dir = tmp_path / "downloads"
    stage_dir = tmp_path / "staging"
    download_dir.mkdir()

    downloaded = download_dir / "Consulta SSA.pdf"
    downloaded.write_bytes(b"%PDF-1.4")

    def fake_run(self):
        return ScrapeResult(
            report_kind="consulta_ssa_print",
            downloaded_path=downloaded,
            started_at="2026-03-15T10:00:00",
            finished_at="2026-03-15T10:00:10",
        )

    monkeypatch.setattr("scrap_report.pipeline.SAMScraper.run", fake_run)

    cfg = ScrapeConfig(
        username="u",
        password="p",
        setor_executor="MEL4",
        setor_emissor="IEE3",
        report_kind="consulta_ssa_print",
        download_dir=download_dir,
        staging_dir=stage_dir,
    )

    result = run_pipeline(cfg, generate_reports=True)

    assert result.status == "ok"
    assert result.staged_path.suffix.lower() == ".pdf"
    assert result.reports == {}
    assert "scrape_ms" in result.telemetry
    assert "stage_ms" in result.telemetry
    assert "report_ms" not in result.telemetry


def test_run_pipeline_from_local_download_pdf_skips_reports(tmp_path: Path):
    download_dir = tmp_path / "downloads"
    stage_dir = tmp_path / "staging"
    download_dir.mkdir()

    downloaded = download_dir / "Consulta SSA.pdf"
    downloaded.write_bytes(b"%PDF-1.4")

    cfg = ScrapeConfig(
        username="u",
        password="p",
        setor_executor="MEL4",
        setor_emissor="IEE3",
        report_kind="consulta_ssa_print",
        download_dir=download_dir,
        staging_dir=stage_dir,
    )

    result = run_pipeline_from_local_download(cfg, generate_reports=True)

    assert result.status == "ok"
    assert result.source_path == downloaded
    assert result.staged_path.suffix.lower() == ".pdf"
    assert result.reports == {}
    assert "find_download_ms" in result.telemetry
    assert "stage_ms" in result.telemetry
    assert "report_ms" not in result.telemetry


def test_run_pipeline_offline_derivadas_relacionadas_uses_custom_parser_reports(
    monkeypatch, tmp_path: Path
):
    download_dir = tmp_path / "downloads"
    stage_dir = tmp_path / "staging"
    download_dir.mkdir()

    downloaded = download_dir / "Derivadas.xlsx"
    pd.DataFrame(
        {
            "Número da SSA": ["202602343", None],
            "Localização": ["T075Q002", None],
            "Setor Emissor": ["IEE3", None],
            "Setor Executor": ["MEL4", None],
            "Situação": ["STE", None],
            "Número da SSA.1": [None, "202602343"],
            "Setor Emissor.1": [None, "IEE3"],
            "Setor Executor.1": [None, "MEL4"],
            "Situação.1": [None, "STE"],
            "Relação": [None, "Derivada da"],
            "Número da SSA.2": [None, "202517662"],
            "Setor Emissor.2": [None, "IEQ1"],
            "Setor Executor.2": [None, "IEE3"],
            "Situação.2": [None, "ADM"],
        }
    ).to_excel(downloaded, index=False)

    def fake_run(self):
        return ScrapeResult(
            report_kind="derivadas_relacionadas",
            downloaded_path=downloaded,
            started_at="2026-03-15T10:00:00",
            finished_at="2026-03-15T10:00:10",
        )

    monkeypatch.setattr("scrap_report.pipeline.SAMScraper.run", fake_run)

    cfg = ScrapeConfig(
        username="u",
        password="p",
        setor_executor="MEL4",
        setor_emissor="IEE3",
        report_kind="derivadas_relacionadas",
        download_dir=download_dir,
        staging_dir=stage_dir,
    )

    result = run_pipeline(cfg, generate_reports=True)

    assert result.status == "ok"
    assert result.staged_path.suffix.lower() == ".xlsx"
    assert "dados" in result.reports
    assert Path(result.reports["dados"]).exists()
    assert "scrape_ms" in result.telemetry
    assert "stage_ms" in result.telemetry
    assert "report_ms" in result.telemetry


def test_run_report_only(tmp_path: Path):
    source = tmp_path / "staging" / "entrada.xlsx"
    source.parent.mkdir(parents=True)
    pd.DataFrame({"Numero da SSA": ["1", "2", "3"]}).to_excel(source, index=False)

    result = run_report_only(
        source_excel=source,
        report_kind="pendentes",
        reports_output_dir=tmp_path / "staging" / "reports",
    )

    assert result.status == "ok"
    assert result.source_path == source
    assert result.staged_path == source
    assert "dados" in result.reports
    assert "report_ms" in result.telemetry


def test_run_report_only_missing_file_raises_typed_error(tmp_path: Path):
    missing = tmp_path / "staging" / "missing.xlsx"
    with pytest.raises(PipelineStepError):
        run_report_only(
            source_excel=missing,
            report_kind="pendentes",
            reports_output_dir=tmp_path / "staging" / "reports",
        )


def test_run_report_only_rejects_non_tabular_kind(tmp_path: Path):
    source = tmp_path / "staging" / "entrada.xlsx"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"x")

    with pytest.raises(PipelineStepError):
        run_report_only(
            source_excel=source,
            report_kind="consulta_ssa_print",
            reports_output_dir=tmp_path / "staging" / "reports",
        )
