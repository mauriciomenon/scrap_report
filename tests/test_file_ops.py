from datetime import datetime
from pathlib import Path

import pytest

from scrap_report.file_ops import build_staged_filename, find_latest_xlsx, stage_download


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
