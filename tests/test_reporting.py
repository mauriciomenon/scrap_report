from pathlib import Path

from openpyxl import Workbook
import pandas as pd

from scrap_report.reporting import (
    artifacts_to_dict,
    load_excel,
    load_derivadas_relacionadas_excel,
    load_excel_for_report,
    export_data_excel,
    export_summary_statistics,
    generate_ssa_report_from_excel,
    generate_text_report,
)


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Numero da SSA": ["001", "002"],
            "Situacao": ["Pendente", "Executada"],
            "Setor Emissor": ["IEE3", "IEE1"],
            "Setor Executor": ["MEL4", "MEL4"],
        }
    )


def _outsystems_like_excel(path: Path) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "SSAs Pendentes Geral"
    sheet.append(["", "", "", "SSAs Pendentes Geral"])
    sheet.append(
        [
            "Numero da SSA",
            "Situacao",
            "Setor Emissor",
            "Setor Executor",
            "Descricao da SSA",
        ]
    )
    sheet.append(["001", "Pendente", "IEE3", "MEL4", "Mantida"])
    sheet.append(["002", "Pendente", "IEE1", "IEE3", "Filtrar emissor"])
    sheet.append(["003", "Pendente", "IEE3", "IEE3", "Filtrar executor"])
    workbook.save(path)
    workbook.close()
    return path


def _derivadas_relacionadas_excel(path: Path) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "SSAs Derivadas e Relacionadas"
    sheet.append(["", "", "", "SSAs Derivadas e Relacionadas"])
    sheet.append(
        [
            "Número da SSA",
            "Localização",
            "Setor Emissor",
            "Setor Executor",
            "Situação",
            "Número da SSA",
            "Setor Emissor",
            "Setor Executor",
            "Situação",
            "Relação",
            "Número da SSA",
            "Setor Emissor",
            "Setor Executor",
            "Situação",
        ]
    )
    sheet.append(["202602343", "T075Q002", "IEE3", "MEL4", "STE", "", "", "", "", "", "", "", "", ""])
    sheet.append(["", "", "", "", "", "202602343", "IEE3", "MEL4", "STE", "Derivada da", "202517662", "IEQ1", "IEE3", "ADM"])
    sheet.append(["202602395", "G097G013", "IEE3", "MEL4", "SEE", "", "", "", "", "", "", "", "", ""])
    sheet.append(["", "", "", "", "", "Sem derivadas em visualização simplificada.", "", "", "", "", "", "", "", ""])
    workbook.save(path)
    workbook.close()
    return path


def test_export_data_excel(tmp_path: Path):
    df = _sample_df()
    out = export_data_excel(df, tmp_path / "dados.xlsx")
    assert out.exists()
    loaded = pd.read_excel(out)
    assert len(loaded) == 2


def test_export_summary_statistics(tmp_path: Path):
    df = _sample_df()
    out = export_summary_statistics(df, tmp_path / "estat.xlsx")
    assert out.exists()
    loaded = pd.read_excel(out)
    assert "Coluna" in loaded.columns


def test_generate_text_report(tmp_path: Path):
    df = _sample_df()
    out = generate_text_report(df, tmp_path / "relatorio.txt")
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "RELATORIO DE SSAS" in content


def test_generate_ssa_report_from_excel(tmp_path: Path):
    df = _sample_df()
    excel = tmp_path / "entrada.xlsx"
    df.to_excel(excel, index=False)

    artifacts = generate_ssa_report_from_excel(excel, tmp_path / "out")
    data = artifacts_to_dict(artifacts)

    assert Path(data["dados"]).exists()
    assert Path(data["estatisticas"]).exists()
    assert Path(data["relatorio_txt"]).exists()


def test_load_derivadas_relacionadas_excel_normalizes_pairs(tmp_path: Path):
    excel = _derivadas_relacionadas_excel(tmp_path / "derivadas.xlsx")
    df = load_derivadas_relacionadas_excel(excel)

    assert list(df.columns) == [
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
    ]
    assert len(df) == 2
    assert df.iloc[0]["ssa_referencia_numero"] == "202602343"
    assert df.iloc[0]["relacao"] == "Derivada da"
    assert df.iloc[0]["ssa_relacionada_destino_numero"] == "202517662"
    assert df.iloc[1]["ssa_referencia_numero"] == "202602395"
    assert df.iloc[1]["observacao"] == "Sem derivadas em visualização simplificada."


def test_load_excel_assigns_suffixes_for_duplicate_headers(tmp_path: Path):
    excel = _derivadas_relacionadas_excel(tmp_path / "derivadas_headers.xlsx")
    df = load_excel(excel)

    assert "Número da SSA" in df.columns
    assert "Número da SSA.1" in df.columns
    assert "Número da SSA.2" in df.columns
    assert "Setor Emissor.1" in df.columns
    assert "Setor Emissor.2" in df.columns


def test_generate_ssa_report_from_excel_derivadas_relacionadas(tmp_path: Path):
    excel = _derivadas_relacionadas_excel(tmp_path / "derivadas.xlsx")

    artifacts = generate_ssa_report_from_excel(
        excel, tmp_path / "out", report_kind="derivadas_relacionadas"
    )
    data = pd.read_excel(artifacts.dados)

    assert len(data) == 2
    assert "ssa_referencia_numero" in data.columns
    assert "observacao" in data.columns


def test_load_excel_for_report_uses_custom_parser_for_derivadas_relacionadas(tmp_path: Path):
    excel = _derivadas_relacionadas_excel(tmp_path / "derivadas_custom_parser.xlsx")

    df = load_excel_for_report(excel, "derivadas_relacionadas")

    assert "ssa_referencia_numero" in df.columns
    assert "observacao" in df.columns


def test_load_excel_detects_real_header_and_filters_scope(tmp_path: Path):
    excel = _outsystems_like_excel(tmp_path / "entrada_outsystems.xlsx")
    df = load_excel(excel, setor_emissor="IEE3", setor_executor="MEL4")

    assert list(df.columns) == [
        "Numero da SSA",
        "Situacao",
        "Setor Emissor",
        "Setor Executor",
        "Descricao da SSA",
    ]
    assert len(df) == 1
    assert df.iloc[0]["Numero da SSA"] == "001"
    assert df.iloc[0]["Setor Emissor"] == "IEE3"
    assert df.iloc[0]["Setor Executor"] == "MEL4"


def test_load_excel_can_filter_only_by_emissor(tmp_path: Path):
    excel = _outsystems_like_excel(tmp_path / "entrada_outsystems_emissor.xlsx")
    df = load_excel(excel, setor_emissor="IEE3", setor_executor="ALL")

    assert len(df) == 2
    assert set(df["Numero da SSA"].astype(str)) == {"001", "003"}


def test_load_excel_can_skip_both_filters(tmp_path: Path):
    excel = _outsystems_like_excel(tmp_path / "entrada_outsystems_all.xlsx")
    df = load_excel(excel, setor_emissor="ALL", setor_executor="ALL")

    assert len(df) == 3
