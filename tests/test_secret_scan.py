from pathlib import Path

from scrap_report.secret_scan import scan_paths


def test_scan_paths_finds_inline_secret(tmp_path: Path):
    file = tmp_path / "sample.py"
    file.write_text("password='abc12345'\n", encoding="utf-8")
    findings = scan_paths([file])
    assert len(findings) == 1
    assert findings[0].rule == "inline_password_key"


def test_scan_paths_no_findings_for_safe_file(tmp_path: Path):
    file = tmp_path / "safe.py"
    file.write_text("value = 'ok'\n", encoding="utf-8")
    findings = scan_paths([file])
    assert findings == []


def test_scan_paths_scans_directories_recursively(tmp_path: Path):
    nested = tmp_path / "nested" / "deep"
    nested.mkdir(parents=True)
    file = nested / "leak.py"
    file.write_text("api_key='abc123456789'\n", encoding="utf-8")
    findings = scan_paths([tmp_path])
    assert len(findings) == 1
    assert findings[0].rule == "api_key_inline"
    assert findings[0].path.endswith("leak.py")


def test_scan_paths_avoids_duplicate_walk_on_overlapping_paths(tmp_path: Path):
    nested = tmp_path / "nested"
    nested.mkdir(parents=True)
    file = nested / "dup.py"
    file.write_text("password='abc12345'\n", encoding="utf-8")
    findings = scan_paths([tmp_path, nested])
    assert len(findings) == 1
    assert findings[0].path.endswith("dup.py")


def test_scan_paths_detects_multiline_assignment(tmp_path: Path):
    file = tmp_path / "multi.yaml"
    file.write_text("api_key:\n  'abc123456789'\n", encoding="utf-8")
    findings = scan_paths([file])
    assert len(findings) == 1
    assert findings[0].rule == "api_key_inline"

