#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SMOKE_USERNAME="${SMOKE_USERNAME:-local_user}"
SMOKE_SETUP_SECRET="${SMOKE_SETUP_SECRET:-0}"
SMOKE_PROMPT_USERNAME="${SMOKE_PROMPT_USERNAME:-0}"
SECRET_SERVICE="${SECRET_SERVICE:-scrap_report.sam}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --smoke-username)
      if [[ $# -lt 2 ]]; then
        echo "[smoke] --smoke-username exige valor" >&2
        exit 2
      fi
      SMOKE_USERNAME="$2"
      shift 2
      ;;
    --prompt-username)
      SMOKE_PROMPT_USERNAME=1
      shift
      ;;
    --setup-secret)
      SMOKE_SETUP_SECRET=1
      shift
      ;;
    --secret-service)
      if [[ $# -lt 2 ]]; then
        echo "[smoke] --secret-service exige valor" >&2
        exit 2
      fi
      SECRET_SERVICE="$2"
      shift 2
      ;;
    *)
      echo "[smoke] argumento invalido: $1" >&2
      exit 2
      ;;
  esac
done

if [[ "${SMOKE_PROMPT_USERNAME}" == "1" || -z "${SMOKE_USERNAME}" ]]; then
  read -r -p "smoke username: " INPUT_USERNAME
  if [[ -n "${INPUT_USERNAME}" ]]; then
    SMOKE_USERNAME="${INPUT_USERNAME}"
  fi
fi
if [[ -z "${SMOKE_USERNAME}" ]]; then
  SMOKE_USERNAME="local_user"
fi

mkdir -p staging downloads

PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || command -v python || true)}"
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "[smoke] python interpreter nao encontrado para preflight de rede" >&2
  exit 1
fi

"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import urlopen

url = "https://pypi.org/simple/wheel/"

try:
    with urlopen(url, timeout=15) as response:  # noqa: S310
        status = getattr(response, "status", 200)
except (HTTPError, URLError, TimeoutError) as exc:
    raise SystemExit(f"[smoke] pypi preflight failed for {url}: {exc}") from exc

if int(status) >= 400:
    raise SystemExit(f"[smoke] pypi preflight returned HTTP {status} for {url}")

print(f"[smoke] pypi preflight ok: {url} (HTTP {status})")
PY

uv sync

uv run --project . python -m compileall -q src tests
uv run --project . ruff check .
uv run --project . --with pytest python -m pytest -q tests/test_contract.py tests/test_cli.py tests/test_pipeline_offline.py tests/test_scraper_contract.py tests/test_file_ops.py tests/test_reporting.py

uv run --project . python -m scrap_report.cli scan-secrets --paths src README.md --output-json staging/scan_secrets.json
uv run --project . python -m scrap_report.cli validate-contract --output-json staging/contract_info.json
uv run --project . python -m scrap_report.cli secret test
if [[ "${SMOKE_SETUP_SECRET}" == "1" ]]; then
  uv run --project . python -m scrap_report.cli secret setup --username "${SMOKE_USERNAME}" --secret-service "${SECRET_SERVICE}"
  uv run --project . python -m scrap_report.cli secret get --username "${SMOKE_USERNAME}" --secret-service "${SECRET_SERVICE}"
fi

uv run --project . --with pandas python -c "import pandas as pd; pd.DataFrame({'Numero da SSA':['1']}).to_excel('downloads/Report.xlsx', index=False)"
uv run --project . python -m scrap_report.cli stage --source downloads/Report.xlsx --staging-dir staging --report-kind pendentes --output-json staging/stage_result.json

LATEST_XLSX="$(
uv run --project . python - <<'PY'
from __future__ import annotations

import json
from pathlib import Path

payload = json.loads(Path("staging/stage_result.json").read_text(encoding="utf-8"))
staged_path = str(payload.get("staged_path", "")).strip()
if not staged_path:
    raise SystemExit("[smoke] stage_result.json sem campo staged_path")
print(staged_path)
PY
)"
if [[ ! -f "${LATEST_XLSX}" ]]; then
  echo "[smoke] staged xlsx nao encontrado: ${LATEST_XLSX}" >&2
  exit 1
fi
uv run --project . python -m scrap_report.cli pipeline --setor IEE3 --report-kind pendentes --staging-dir staging --report-only --source-excel "$LATEST_XLSX" --output-json staging/pipeline_report_only.json

cp -f "$LATEST_XLSX" downloads/Report_latest.xlsx
if [[ "${SMOKE_SETUP_SECRET}" == "1" ]]; then
  uv run --project . python -m scrap_report.cli ingest-latest --setor IEE3 --report-kind pendentes --download-dir downloads --staging-dir staging --username "${SMOKE_USERNAME}" --secret-service "${SECRET_SERVICE}" --secure-required --output-json staging/ingest_result.json
else
  SMOKE_TRANSITIONAL_PASSWORD="$(date +%s%N)"
  SAM_PASSWORD="${SMOKE_TRANSITIONAL_PASSWORD}" uv run --project . python -m scrap_report.cli ingest-latest --setor IEE3 --report-kind pendentes --download-dir downloads --staging-dir staging --username "${SMOKE_USERNAME}" --allow-transitional-plaintext --output-json staging/ingest_result.json
fi

SMOKE_USERNAME_ENV="${SMOKE_USERNAME}" SECRET_SERVICE_ENV="${SECRET_SERVICE}" SMOKE_SETUP_SECRET_ENV="${SMOKE_SETUP_SECRET}" uv run --project . python - <<'PY'
from __future__ import annotations

import json
import os
import platform
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

evidence = {
    "platform_label": "debian13",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "host": platform.node(),
    "python_version": platform.python_version(),
    "inputs": {
        "smoke_username": os.environ.get("SMOKE_USERNAME_ENV", ""),
        "secret_service": os.environ.get("SECRET_SERVICE_ENV", ""),
        "setup_secret": os.environ.get("SMOKE_SETUP_SECRET_ENV", "0") == "1",
    },
    "checks": {
        "py_compile": "ok",
        "ruff": "ok",
        "pytest": "ok",
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
