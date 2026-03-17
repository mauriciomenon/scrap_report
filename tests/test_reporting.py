from pathlib import Path

from openpyxl import Workbook
import pandas as pd

from scrap_report.reporting import (
    artifacts_to_dict,
    load_excel,
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


def test_load_excel_detects_real_header_and_filters_scope(tmp_path: Path):
    excel = _outsystems_like_excel(tmp_path / "entrada_outsystems.xlsx")
    df = load_excel(excel)

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
