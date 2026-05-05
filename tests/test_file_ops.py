from datetime import datetime
from pathlib import Path

import pytest

from scrap_report.file_ops import (
    build_staged_filename,
    collect_available_file_artifacts,
    find_latest_download,
    find_latest_xlsx,
    stage_download,
    with_available_file_artifacts,
)


def test_build_staged_filename_contains_report_kind():
    filename = build_staged_filename("Report.xlsx", "pendentes", datetime(2026, 3, 15, 12, 0, 0))
    assert filename.startswith("pendentes_Report_20260315_120000_")
    assert filename.endswith(".xlsx")


def test_stage_download_moves_file(tmp_path: Path):
    source = tmp_path / "Report.xlsx"
    source.write_bytes(b"abc")

    staging_dir = tmp_path / "stage"
    staged = stage_download(source, staging_dir, "pendentes")

    assert staged.exists()
    assert not source.exists()


def test_find_latest_xlsx_returns_most_recent(tmp_path: Path):
    f1 = tmp_path / "a.xlsx"
    f2 = tmp_path / "b.xlsx"
    f1.write_bytes(b"1")
    f2.write_bytes(b"2")

    latest = find_latest_xlsx(tmp_path)
    assert latest.name in {"a.xlsx", "b.xlsx"}


def test_find_latest_xlsx_raises_when_empty(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        find_latest_xlsx(tmp_path)


def test_find_latest_download_supports_pdf(tmp_path: Path):
    f1 = tmp_path / "a.pdf"
    f2 = tmp_path / "b.pdf"
    f1.write_bytes(b"1")
    f2.write_bytes(b"2")

    latest = find_latest_download(tmp_path, (".pdf",))
    assert latest.name in {"a.pdf", "b.pdf"}


def test_collect_available_file_artifacts_filters_invalid_and_excluded_keys(tmp_path: Path):
    staged = tmp_path / "staging" / "ok.xlsx"
    report = tmp_path / "staging" / "reports" / "dados.xlsx"
    missing = tmp_path / "downloads" / "old.xlsx"
    old_dir = tmp_path / "downloads"
    staged.parent.mkdir(parents=True)
    report.parent.mkdir(parents=True)
    old_dir.mkdir(parents=True)
    staged.write_bytes(b"xlsx")
    report.write_bytes(b"report")

    payload = {
        "output_path": str(old_dir),
        "source_path": str(missing),
        "staged_path": str(staged),
        "manifest_json": str(staged),
        "exports": {
            "dir": str(old_dir),
            "data_xlsx": str(report),
            "manifest_json": str(staged),
            "count": 1,
        },
        "reports": {
            "dados": str(report),
            "old": str(missing),
            "mode": "search",
        },
    }

    available = collect_available_file_artifacts(payload)

    assert "source_path" not in available
    assert "manifest_json" not in available
    assert available["staged_path"] == str(staged)
    assert available["exports"] == {"data_xlsx": str(report)}
    assert available["reports"] == {"dados": str(report)}
    assert with_available_file_artifacts(payload)["available_artifacts"] == available


def test_with_available_file_artifacts_removes_stale_actions(tmp_path: Path):
    old = tmp_path / "old.xlsx"
    old.write_bytes(b"old")

    payload = {
        "status": "ok",
        "staged_path": str(tmp_path / "missing.xlsx"),
        "available_artifacts": {"staged_path": str(old)},
    }

    enriched = with_available_file_artifacts(payload)

    assert "available_artifacts" not in enriched


def test_collect_available_file_artifacts_accepts_existing_relative_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    relative = Path("artifact.xlsx")
    relative.write_bytes(b"xlsx")

    available = collect_available_file_artifacts({"staged_path": str(relative)})

    assert available == {"staged_path": str(relative)}
