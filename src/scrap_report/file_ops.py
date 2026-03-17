"""Operacoes de arquivo para staging de excel."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path


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
