from pathlib import Path

import pandas as pd

from scrap_report.reporting import (
    artifacts_to_dict,
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
            "Setor Executor": ["IEE3", "IEE3"],
        }
    )


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
