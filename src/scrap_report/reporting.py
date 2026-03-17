"""Geracao de artefatos de relatorio a partir de Excel."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd

TARGET_SETOR_EMISSOR = "IEE3"
TARGET_SETOR_EXECUTOR = "MEL4"


@dataclass(slots=True)
class ReportArtifacts:
    dados: Path
    estatisticas: Path
    relatorio_txt: Path


def _nonempty_count(values: pd.Series) -> int:
    return int(sum(value not in (None, "") and not pd.isna(value) for value in values))


def _detect_header_row(raw_df: pd.DataFrame) -> int:
    for index in range(min(len(raw_df), 10)):
        row = raw_df.iloc[index]
        normalized = [
            str(value).strip().lower()
            for value in row
            if value not in (None, "") and not pd.isna(value)
        ]
        if "numero da ssa" in normalized or "número da ssa" in normalized:
            return index

    best_index = 0
    best_score = -1
    for index in range(min(len(raw_df), 10)):
        score = _nonempty_count(raw_df.iloc[index])
        if score > best_score:
            best_index = index
            best_score = score
    return best_index


def _normalize_columns(values: pd.Series) -> list[str]:
    columns: list[str] = []
    for index, value in enumerate(values):
        if value in (None, "") or pd.isna(value):
            columns.append(f"Unnamed: {index}")
            continue
        columns.append(str(value).strip())
    return columns


def _filter_report_scope(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df.copy()
    if "Setor Executor" in filtered.columns:
        filtered = filtered[filtered["Setor Executor"].astype(str).str.strip() == TARGET_SETOR_EXECUTOR]
    if "Setor Emissor" in filtered.columns:
        filtered = filtered[filtered["Setor Emissor"].astype(str).str.strip() == TARGET_SETOR_EMISSOR]
    return filtered.reset_index(drop=True)


def load_excel(excel_path: Path) -> pd.DataFrame:
    path = Path(excel_path)
    if not path.exists():
        raise FileNotFoundError(f"excel nao encontrado: {path}")
    raw_df = pd.read_excel(path, header=None)
    header_row = _detect_header_row(raw_df)
    data = raw_df.iloc[header_row + 1 :].copy()
    data.columns = _normalize_columns(raw_df.iloc[header_row])
    data = data.dropna(axis=0, how="all").dropna(axis=1, how="all").reset_index(drop=True)
    return _filter_report_scope(data)


def export_data_excel(df: pd.DataFrame, filename: Path) -> Path:
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Dados", index=False)
    return path


def export_summary_statistics(df: pd.DataFrame, filename: Path) -> Path:
    summary_rows = []
    for column in df.columns:
        col_data = df[column]
        summary_rows.append(
            {
                "Coluna": column,
                "Tipo": str(col_data.dtype),
                "Total": int(len(col_data)),
                "Unicos": int(col_data.nunique(dropna=True)),
                "Nulos": int(col_data.isna().sum()),
            }
        )
    summary_df = pd.DataFrame(summary_rows)
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Resumo", index=False)
    return path


def generate_text_report(df: pd.DataFrame, filename: Path) -> Path:
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "=" * 60,
        "RELATORIO DE SSAS",
        "=" * 60,
        f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        f"Total de Registros: {len(df)}",
        "",
        "COLUNAS:",
    ]

    for column in df.columns:
        unique_count = df[column].nunique(dropna=True)
        null_count = int(df[column].isna().sum())
        lines.append(f"- {column}: {unique_count} unicos, {null_count} nulos")

    lines.extend(["", "=" * 60, "FIM DO RELATORIO", "=" * 60])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def generate_ssa_report_from_excel(excel_path: Path, output_dir: Path) -> ReportArtifacts:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    df = load_excel(excel_path)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    dados = export_data_excel(df, output / f"ssas_dados_{ts}.xlsx")
    estat = export_summary_statistics(df, output / f"ssas_estatisticas_{ts}.xlsx")
    txt = generate_text_report(df, output / f"ssas_relatorio_{ts}.txt")

    return ReportArtifacts(dados=dados, estatisticas=estat, relatorio_txt=txt)


def artifacts_to_dict(artifacts: ReportArtifacts) -> Dict[str, str]:
    return {
        "dados": str(artifacts.dados),
        "estatisticas": str(artifacts.estatisticas),
        "relatorio_txt": str(artifacts.relatorio_txt),
    }
