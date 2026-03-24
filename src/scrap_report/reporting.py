"""Geracao de artefatos de relatorio a partir de Excel."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
import unicodedata

import pandas as pd

from .config import normalize_setor_filter, report_kind_uses_custom_parser
from .sam_api import SAM_API_EXPORT_COLUMNS
DERIVADAS_RELACIONADAS_COLUMNS = (
    "ssa_referencia_numero",
    "ssa_referencia_localizacao",
    "ssa_referencia_setor_emissor",
    "ssa_referencia_setor_executor",
    "ssa_referencia_situacao",
    "ssa_relacionada_numero",
    "ssa_relacionada_setor_emissor",
    "ssa_relacionada_setor_executor",
    "ssa_relacionada_situacao",
    "relacao",
    "ssa_relacionada_destino_numero",
    "ssa_relacionada_destino_setor_emissor",
    "ssa_relacionada_destino_setor_executor",
    "ssa_relacionada_destino_situacao",
    "observacao",
)


@dataclass(slots=True)
class ReportArtifacts:
    dados: Path
    estatisticas: Path
    relatorio_txt: Path


@dataclass(slots=True)
class SAMApiArtifacts:
    data_csv: Path
    data_xlsx: Path
    summary_xlsx: Path


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
    seen: dict[str, int] = {}
    for index, value in enumerate(values):
        if value in (None, "") or pd.isna(value):
            base_name = f"Unnamed: {index}"
        else:
            base_name = str(value).strip()

        duplicate_index = seen.get(base_name, 0)
        seen[base_name] = duplicate_index + 1
        if duplicate_index == 0:
            columns.append(base_name)
            continue
        columns.append(f"{base_name}.{duplicate_index}")
    return columns


def _filter_report_scope(
    df: pd.DataFrame,
    setor_emissor: str | None = None,
    setor_executor: str | None = None,
) -> pd.DataFrame:
    filtered = df.copy()
    normalized_executor = normalize_setor_filter(setor_executor)
    normalized_emissor = normalize_setor_filter(setor_emissor)
    if normalized_executor and "Setor Executor" in filtered.columns:
        filtered = (
            filtered[filtered["Setor Executor"].astype(str).str.strip().str.upper() == normalized_executor]
        )
    if normalized_emissor and "Setor Emissor" in filtered.columns:
        filtered = (
            filtered[filtered["Setor Emissor"].astype(str).str.strip().str.upper() == normalized_emissor]
        )
    return filtered.reset_index(drop=True)


def _normalize_nullable_text(value: object) -> str | None:
    if value in (None, "") or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _normalize_column_key(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = text.encode("ascii", "ignore").decode("ascii")
    return text.strip().lower()


def _resolve_first_column_name(df: pd.DataFrame, *candidates: str) -> str:
    normalized_candidates = {_normalize_column_key(item) for item in candidates}
    for column in df.columns:
        if _normalize_column_key(column) in normalized_candidates:
            return str(column)
    raise KeyError(candidates[0])


def _get_first_column_series(df: pd.DataFrame, *candidates: str) -> pd.Series:
    column_name = _resolve_first_column_name(df, *candidates)
    data = df.loc[:, column_name]
    if isinstance(data, pd.DataFrame):
        return data.iloc[:, 0]
    return data


def load_excel(
    excel_path: Path,
    setor_emissor: str | None = None,
    setor_executor: str | None = None,
) -> pd.DataFrame:
    path = Path(excel_path)
    if not path.exists():
        raise FileNotFoundError(f"excel nao encontrado: {path}")
    data = _load_outsystems_table(path)
    return _filter_report_scope(data, setor_emissor=setor_emissor, setor_executor=setor_executor)


def _load_outsystems_table(path: Path) -> pd.DataFrame:
    raw_df = pd.read_excel(path, header=None)
    header_row = _detect_header_row(raw_df)
    data = raw_df.iloc[header_row + 1 :].copy()
    data.columns = _normalize_columns(raw_df.iloc[header_row])
    data = data.dropna(axis=0, how="all").dropna(axis=1, how="all").reset_index(drop=True)
    return data


def load_derivadas_relacionadas_excel(
    excel_path: Path,
    setor_emissor: str | None = None,
    setor_executor: str | None = None,
) -> pd.DataFrame:
    path = Path(excel_path)
    if not path.exists():
        raise FileNotFoundError(f"excel nao encontrado: {path}")

    base_df = _load_outsystems_table(path)
    if base_df.empty:
        return pd.DataFrame(columns=list(DERIVADAS_RELACIONADAS_COLUMNS))

    work = base_df.copy()
    primary_number_col = _resolve_first_column_name(work, "Número da SSA", "Numero da SSA")
    localizacao_col = _resolve_first_column_name(work, "Localização", "Localizacao")
    setor_emissor_col = _resolve_first_column_name(work, "Setor Emissor")
    setor_executor_col = _resolve_first_column_name(work, "Setor Executor")
    situacao_col = _resolve_first_column_name(work, "Situação", "Situacao")
    related_number_col = _resolve_first_column_name(work, "Número da SSA.1", "Numero da SSA.1")
    related_emissor_col = _resolve_first_column_name(work, "Setor Emissor.1")
    related_executor_col = _resolve_first_column_name(work, "Setor Executor.1")
    related_situacao_col = _resolve_first_column_name(work, "Situação.1", "Situacao.1")
    relacao_col = _resolve_first_column_name(work, "Relação", "Relacao")
    target_number_col = _resolve_first_column_name(work, "Número da SSA.2", "Numero da SSA.2")
    target_emissor_col = _resolve_first_column_name(work, "Setor Emissor.2")
    target_executor_col = _resolve_first_column_name(work, "Setor Executor.2")
    target_situacao_col = _resolve_first_column_name(work, "Situação.2", "Situacao.2")

    work["_is_detail_row"] = _get_first_column_series(work, "Número da SSA", "Numero da SSA").isna()
    work[primary_number_col] = _get_first_column_series(work, "Número da SSA", "Numero da SSA").ffill()
    work[localizacao_col] = _get_first_column_series(work, "Localização", "Localizacao").ffill()
    work[setor_emissor_col] = _get_first_column_series(work, "Setor Emissor").ffill()
    work[setor_executor_col] = _get_first_column_series(work, "Setor Executor").ffill()
    work[situacao_col] = _get_first_column_series(work, "Situação", "Situacao").ffill()

    work = _filter_report_scope(work, setor_emissor=setor_emissor, setor_executor=setor_executor)
    detail_mask = work["_is_detail_row"]

    detail = work[detail_mask].copy()
    if detail.empty:
        return pd.DataFrame(columns=list(DERIVADAS_RELACIONADAS_COLUMNS))

    observation_col = "Número da SSA.1"
    observation_mask = detail[observation_col].astype(str).str.contains(
        "Sem derivadas em visualização simplificada", na=False
    )

    normalized = pd.DataFrame(
        {
            "ssa_referencia_numero": detail[primary_number_col].map(_normalize_nullable_text),
            "ssa_referencia_localizacao": detail[localizacao_col].map(_normalize_nullable_text),
            "ssa_referencia_setor_emissor": detail[setor_emissor_col].map(_normalize_nullable_text),
            "ssa_referencia_setor_executor": detail[setor_executor_col].map(_normalize_nullable_text),
            "ssa_referencia_situacao": detail[situacao_col].map(_normalize_nullable_text),
            "ssa_relacionada_numero": detail[related_number_col].map(_normalize_nullable_text),
            "ssa_relacionada_setor_emissor": detail[related_emissor_col].map(_normalize_nullable_text),
            "ssa_relacionada_setor_executor": detail[related_executor_col].map(_normalize_nullable_text),
            "ssa_relacionada_situacao": detail[related_situacao_col].map(_normalize_nullable_text),
            "relacao": detail[relacao_col].map(_normalize_nullable_text),
            "ssa_relacionada_destino_numero": detail[target_number_col].map(_normalize_nullable_text),
            "ssa_relacionada_destino_setor_emissor": detail[target_emissor_col].map(_normalize_nullable_text),
            "ssa_relacionada_destino_setor_executor": detail[target_executor_col].map(_normalize_nullable_text),
            "ssa_relacionada_destino_situacao": detail[target_situacao_col].map(_normalize_nullable_text),
            "observacao": pd.Series([None] * len(detail), index=detail.index, dtype="object"),
        }
    )

    normalized.loc[observation_mask, "observacao"] = (
        detail.loc[observation_mask, related_number_col].map(_normalize_nullable_text)
    )
    normalized.loc[observation_mask, "ssa_relacionada_numero"] = None
    normalized.loc[observation_mask, "ssa_relacionada_setor_emissor"] = None
    normalized.loc[observation_mask, "ssa_relacionada_setor_executor"] = None
    normalized.loc[observation_mask, "ssa_relacionada_situacao"] = None
    normalized.loc[observation_mask, "relacao"] = None
    normalized.loc[observation_mask, "ssa_relacionada_destino_numero"] = None
    normalized.loc[observation_mask, "ssa_relacionada_destino_setor_emissor"] = None
    normalized.loc[observation_mask, "ssa_relacionada_destino_setor_executor"] = None
    normalized.loc[observation_mask, "ssa_relacionada_destino_situacao"] = None

    return normalized.reset_index(drop=True)


def load_excel_for_report(
    excel_path: Path,
    report_kind: str,
    setor_emissor: str | None = None,
    setor_executor: str | None = None,
) -> pd.DataFrame:
    if report_kind_uses_custom_parser(report_kind):
        return load_derivadas_relacionadas_excel(
            excel_path,
            setor_emissor=setor_emissor,
            setor_executor=setor_executor,
        )
    return load_excel(excel_path, setor_emissor=setor_emissor, setor_executor=setor_executor)


def export_data_excel(df: pd.DataFrame, filename: Path) -> Path:
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Dados", index=False)
    return path


def export_data_csv(df: pd.DataFrame, filename: Path) -> Path:
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    return path


def build_sam_api_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=list(SAM_API_EXPORT_COLUMNS))
    df = pd.DataFrame(records)
    for column in SAM_API_EXPORT_COLUMNS:
        if column not in df.columns:
            df[column] = None
    ordered_columns = list(SAM_API_EXPORT_COLUMNS) + [
        column for column in df.columns if column not in SAM_API_EXPORT_COLUMNS
    ]
    return df.loc[:, ordered_columns]


def build_sam_api_summary_frames(records: list[dict[str, Any]]) -> dict[str, pd.DataFrame]:
    data_df = build_sam_api_dataframe(records)
    overview_df = pd.DataFrame(
        [
            {
                "metric": "total",
                "value": int(len(data_df)),
            },
            {
                "metric": "detail_count",
                "value": int(data_df["detail_present"].fillna(False).astype(bool).sum()),
            },
            {
                "metric": "without_detail_count",
                "value": int(len(data_df) - data_df["detail_present"].fillna(False).astype(bool).sum()),
            },
        ]
    )

    def _group_counts(column: str) -> pd.DataFrame:
        if column not in data_df.columns:
            return pd.DataFrame(columns=[column, "count"])
        values = data_df[column].fillna("UNKNOWN")
        counts = values.groupby(values, dropna=False).size()
        grouped = pd.DataFrame(
            {
                column: list(counts.index),
                "count": counts.astype(int).tolist(),
            }
        )
        return grouped.sort_values(by=[column]).reset_index(drop=True)

    return {
        "overview": overview_df,
        "by_executor": _group_counts("executor_sector"),
        "by_emitter": _group_counts("emitter_sector"),
        "by_year_week": _group_counts("year_week"),
    }


def export_sam_api_summary_excel(records: list[dict[str, Any]], filename: Path) -> Path:
    frames = build_sam_api_summary_frames(records)
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, frame in frames.items():
            frame.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    return path


def export_sam_api_artifacts(records: list[dict[str, Any]], output_dir: Path, prefix: str) -> SAMApiArtifacts:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    data_df = build_sam_api_dataframe(records)
    data_csv = export_data_csv(data_df, output / f"{prefix}_dados_{timestamp}.csv")
    data_xlsx = export_data_excel(data_df, output / f"{prefix}_dados_{timestamp}.xlsx")
    summary_xlsx = export_sam_api_summary_excel(records, output / f"{prefix}_resumo_{timestamp}.xlsx")
    return SAMApiArtifacts(data_csv=data_csv, data_xlsx=data_xlsx, summary_xlsx=summary_xlsx)


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


def generate_ssa_report_from_excel(
    excel_path: Path,
    output_dir: Path,
    report_kind: str = "pendentes",
    setor_emissor: str | None = None,
    setor_executor: str | None = None,
) -> ReportArtifacts:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    df = load_excel_for_report(
        excel_path,
        report_kind,
        setor_emissor=setor_emissor,
        setor_executor=setor_executor,
    )
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
        "data_xlsx": str(artifacts.dados),
        "summary_xlsx": str(artifacts.estatisticas),
        "report_txt": str(artifacts.relatorio_txt),
    }


def sam_api_artifacts_to_dict(artifacts: SAMApiArtifacts) -> Dict[str, str]:
    return {
        "csv": str(artifacts.data_csv),
        "xlsx": str(artifacts.data_xlsx),
        "data_csv": str(artifacts.data_csv),
        "data_xlsx": str(artifacts.data_xlsx),
        "summary_xlsx": str(artifacts.summary_xlsx),
    }
