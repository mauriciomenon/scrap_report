"""Geracao de artefatos de relatorio a partir de Excel."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd


@dataclass(slots=True)
class ReportArtifacts:
    dados: Path
    estatisticas: Path
    relatorio_txt: Path


def load_excel(excel_path: Path) -> pd.DataFrame:
    path = Path(excel_path)
    if not path.exists():
        raise FileNotFoundError(f"excel nao encontrado: {path}")
    return pd.read_excel(path)


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
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

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
