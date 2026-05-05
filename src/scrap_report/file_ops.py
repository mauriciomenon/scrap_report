"""Operacoes de arquivo para staging de excel."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_PATH_ARTIFACT_FIELDS = frozenset(
    {
        "downloaded_path",
        "output_path",
        "source_path",
        "staged_path",
    }
)
DEFAULT_PATH_ARTIFACT_MAP_FIELDS = frozenset({"exports", "reports"})
DEFAULT_NON_PATH_ARTIFACT_KEYS = frozenset({"mode"})


def build_staged_filename(source_name: str, report_kind: str, timestamp: datetime | None = None) -> str:
    ts = timestamp or datetime.now()
    stem = Path(source_name).stem
    suffix = Path(source_name).suffix or ".xlsx"
    digest = hashlib.sha1(source_name.encode("utf-8")).hexdigest()[:8]
    return f"{report_kind}_{stem}_{ts.strftime('%Y%m%d_%H%M%S')}_{digest}{suffix}"


def stage_download(source_path: Path, staging_dir: Path, report_kind: str, overwrite: bool = False) -> Path:
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"arquivo de origem nao encontrado: {source}")

    staging_dir.mkdir(parents=True, exist_ok=True)
    target = staging_dir / build_staged_filename(source.name, report_kind)

    if target.exists() and not overwrite:
        raise FileExistsError(f"arquivo de destino ja existe: {target}")

    source.rename(target)
    return target


def find_latest_download(download_dir: Path, suffixes: tuple[str, ...]) -> Path:
    base = Path(download_dir)
    normalized = {suffix.lower() for suffix in suffixes}
    candidates = sorted(
        (path for path in base.iterdir() if path.is_file() and path.suffix.lower() in normalized),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        joined = ", ".join(sorted(normalized))
        raise FileNotFoundError(f"nenhum arquivo {joined} encontrado em {base}")
    return candidates[0]


def find_latest_xlsx(download_dir: Path) -> Path:
    return find_latest_download(download_dir, (".xlsx",))


def existing_file_artifact_path(value: Any) -> str | None:
    if isinstance(value, Path):
        path = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        path = Path(text)
    else:
        return None
    if not path.is_file():
        return None
    return str(path)


def collect_available_file_artifacts(payload: dict[str, Any]) -> dict[str, Any]:
    available: dict[str, Any] = {}
    for field_name in sorted(DEFAULT_PATH_ARTIFACT_FIELDS):
        path = existing_file_artifact_path(payload.get(field_name))
        if path:
            available[field_name] = path

    for map_name in sorted(DEFAULT_PATH_ARTIFACT_MAP_FIELDS):
        values = payload.get(map_name)
        if not isinstance(values, dict):
            continue
        available_values: dict[str, str] = {}
        for key, value in values.items():
            key_text = str(key)
            if key_text in DEFAULT_NON_PATH_ARTIFACT_KEYS:
                continue
            path = existing_file_artifact_path(value)
            if path:
                available_values[key_text] = path
        if available_values:
            available[map_name] = available_values
    return available


def with_available_file_artifacts(payload: dict[str, Any]) -> dict[str, Any]:
    available = collect_available_file_artifacts(payload)
    if not available:
        return payload
    return {**payload, "available_artifacts": available}
