from pathlib import Path

from scrap_report.secret_scan import scan_paths


def test_scan_paths_finds_inline_secret(tmp_path: Path):
    file = tmp_path / "sample.py"
    file.write_text("password='abc123'\n", encoding="utf-8")
    findings = scan_paths([file])
    assert len(findings) == 1
    assert findings[0].rule == "inline_password_key"


def test_scan_paths_no_findings_for_safe_file(tmp_path: Path):
    file = tmp_path / "safe.py"
    file.write_text("value = 'ok'\n", encoding="utf-8")
    findings = scan_paths([file])
    assert findings == []

