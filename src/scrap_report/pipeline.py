"""Orquestracao do pipeline de scraping -> staging -> relatorio."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Dict

from .config import (
    ScrapeConfig,
    report_kind_download_suffixes,
    report_kind_uses_excel_output,
)
from .errors import PipelineStepError
from .file_ops import find_latest_download, stage_download
from .reporting import artifacts_to_dict, generate_ssa_report_from_excel
from .scraper import SAMScraper


@dataclass(slots=True)
class PipelineResult:
    status: str
    report_kind: str
    source_path: Path
    staged_path: Path
    reports: Dict[str, str]
    telemetry: Dict[str, int]


def run_pipeline(config: ScrapeConfig, generate_reports: bool = True) -> PipelineResult:
    telemetry: Dict[str, int] = {}
    scraper = SAMScraper(config)
    try:
        t0 = time.perf_counter()
        scrape_result = scraper.run()
        telemetry["scrape_ms"] = int((time.perf_counter() - t0) * 1000)
    except Exception as exc:
        raise PipelineStepError("scrape", str(exc)) from exc

    try:
        t0 = time.perf_counter()
        staged = stage_download(
            source_path=scrape_result.downloaded_path,
            staging_dir=config.staging_dir,
            report_kind=config.report_kind,
            overwrite=False,
        )
        telemetry["stage_ms"] = int((time.perf_counter() - t0) * 1000)
    except Exception as exc:
        raise PipelineStepError("stage", str(exc)) from exc

    reports: Dict[str, str] = {}
    if generate_reports and report_kind_uses_excel_output(config.report_kind):
        try:
            t0 = time.perf_counter()
            artifacts = generate_ssa_report_from_excel(
                excel_path=staged,
                output_dir=config.staging_dir / "reports",
                report_kind=config.report_kind,
                setor_emissor=config.setor_emissor,
                setor_executor=config.setor_executor,
            )
            reports = artifacts_to_dict(artifacts)
            telemetry["report_ms"] = int((time.perf_counter() - t0) * 1000)
        except Exception as exc:
            raise PipelineStepError("report", str(exc)) from exc

    return PipelineResult(
        status="ok",
        report_kind=config.report_kind,
        source_path=scrape_result.downloaded_path,
        staged_path=staged,
        reports=reports,
        telemetry=telemetry,
    )


def run_pipeline_from_local_download(
    config: ScrapeConfig, generate_reports: bool = True
) -> PipelineResult:
    telemetry: Dict[str, int] = {}
    try:
        t0 = time.perf_counter()
        source = find_latest_download(
            config.download_dir,
            report_kind_download_suffixes(config.report_kind),
        )
        telemetry["find_download_ms"] = int((time.perf_counter() - t0) * 1000)
    except Exception as exc:
        raise PipelineStepError("find_download", str(exc)) from exc
    try:
        t0 = time.perf_counter()
        staged = stage_download(
            source_path=source,
            staging_dir=config.staging_dir,
            report_kind=config.report_kind,
            overwrite=False,
        )
        telemetry["stage_ms"] = int((time.perf_counter() - t0) * 1000)
    except Exception as exc:
        raise PipelineStepError("stage", str(exc)) from exc

    reports: Dict[str, str] = {}
    if generate_reports and report_kind_uses_excel_output(config.report_kind):
        try:
            t0 = time.perf_counter()
            artifacts = generate_ssa_report_from_excel(
                excel_path=staged,
                output_dir=config.staging_dir / "reports",
                report_kind=config.report_kind,
                setor_emissor=config.setor_emissor,
                setor_executor=config.setor_executor,
            )
            reports = artifacts_to_dict(artifacts)
            telemetry["report_ms"] = int((time.perf_counter() - t0) * 1000)
        except Exception as exc:
            raise PipelineStepError("report", str(exc)) from exc

    return PipelineResult(
        status="ok",
        report_kind=config.report_kind,
        source_path=source,
        staged_path=staged,
        reports=reports,
        telemetry=telemetry,
    )


def run_report_only(
    source_excel: Path,
    report_kind: str,
    reports_output_dir: Path,
    setor_emissor: str | None = None,
    setor_executor: str | None = None,
) -> PipelineResult:
    telemetry: Dict[str, int] = {}
    if not report_kind_uses_excel_output(report_kind):
        raise PipelineStepError(
            "report",
            "report_only indisponivel para report_kind sem excel",
        )
    source = Path(source_excel)
    if not source.exists():
        raise PipelineStepError("source_excel", f"excel nao encontrado: {source}")

    try:
        t0 = time.perf_counter()
        artifacts = generate_ssa_report_from_excel(
            excel_path=source,
            output_dir=reports_output_dir,
            report_kind=report_kind,
            setor_emissor=setor_emissor,
            setor_executor=setor_executor,
        )
        reports = artifacts_to_dict(artifacts)
        telemetry["report_ms"] = int((time.perf_counter() - t0) * 1000)
    except Exception as exc:
        raise PipelineStepError("report", str(exc)) from exc

    return PipelineResult(
        status="ok",
        report_kind=report_kind,
        source_path=source,
        staged_path=source,
        reports=reports,
        telemetry=telemetry,
    )
