#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p staging downloads

uv sync

uv run --project . python -m py_compile src/scrap_report/*.py tests/*.py
uv run --project . ruff check .
uv run --project . --with pytest python -m pytest -q tests/test_contract.py tests/test_cli.py tests/test_pipeline_offline.py tests/test_scraper_contract.py tests/test_file_ops.py tests/test_reporting.py

uv run --project . python -m scrap_report.cli scan-secrets --paths src tests README.md --output-json staging/scan_secrets.json
uv run --project . python -m scrap_report.cli validate-contract --output-json staging/contract_info.json
uv run --project . python -m scrap_report.cli secret test

uv run --project . --with pandas python -c "import pandas as pd; pd.DataFrame({'Numero da SSA':['1']}).to_excel('downloads/Report.xlsx', index=False)"
uv run --project . python -m scrap_report.cli stage --source downloads/Report.xlsx --staging-dir staging --report-kind pendentes --output-json staging/stage_result.json

LATEST_XLSX="$(find staging -maxdepth 1 -type f -name '*.xlsx' | head -1)"
uv run --project . python -m scrap_report.cli pipeline --setor IEE3 --report-kind pendentes --staging-dir staging --report-only --source-excel "$LATEST_XLSX" --output-json staging/pipeline_report_only.json

cp -f "$LATEST_XLSX" downloads/Report_latest.xlsx
uv run --project . python -m scrap_report.cli ingest-latest --setor IEE3 --report-kind pendentes --download-dir downloads --staging-dir staging --username local_user --password local_pass --output-json staging/ingest_result.json

uv run --project . python - <<'PY'
from __future__ import annotations

import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

root = Path(".")
staging = root / "staging"
evidence_path = staging / "smoke_evidence_debian13.json"

def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

scan = _load_json(staging / "scan_secrets.json")
contract = _load_json(staging / "contract_info.json")
stage = _load_json(staging / "stage_result.json")
report_only = _load_json(staging / "pipeline_report_only.json")
ingest = _load_json(staging / "ingest_result.json")

pytest_cmd = [
    "uv",
    "run",
    "--project",
    ".",
    "--with",
    "pytest",
    "python",
    "-m",
    "pytest",
    "-q",
    "tests/test_contract.py",
    "tests/test_cli.py",
    "tests/test_pipeline_offline.py",
    "tests/test_scraper_contract.py",
    "tests/test_file_ops.py",
    "tests/test_reporting.py",
]
pytest_result = subprocess.run(pytest_cmd, capture_output=True, text=True, check=False)  # noqa: S603
pytest_ok = pytest_result.returncode == 0

evidence = {
    "platform_label": "debian13_or_macos_local",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "host": platform.node(),
    "python_version": platform.python_version(),
    "checks": {
        "py_compile": "ok",
        "ruff": "ok",
        "pytest": "ok" if pytest_ok else "error",
        "scan_secrets": scan.get("status"),
        "validate_contract": contract.get("status"),
        "stage": stage.get("status"),
        "pipeline_report_only": report_only.get("status"),
        "ingest_latest": ingest.get("status"),
    },
    "artifacts": {
        "scan_secrets_json": "staging/scan_secrets.json",
        "contract_info_json": "staging/contract_info.json",
        "stage_result_json": "staging/stage_result.json",
        "pipeline_report_only_json": "staging/pipeline_report_only.json",
        "ingest_result_json": "staging/ingest_result.json",
    },
}

evidence_path.write_text(json.dumps(evidence, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
print(f"[smoke] evidence written: {evidence_path}")
PY

echo "smoke_debian13.sh: done"
