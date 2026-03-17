import pytest

from scrap_report.scraper import SAMLocators, SAMScraper


def test_resolve_report_navigation_pendentes():
    selector = SAMScraper._resolve_report_navigation("pendentes")
    assert selector.endswith("/SAM_SMA_Reports/PendingGeneralSSAs.aspx")


def test_resolve_report_navigation_executadas():
    selector = SAMScraper._resolve_report_navigation("executadas")
    assert selector.endswith("/SAM_SMA_Reports/SSAsExecuted.aspx")


def test_resolve_report_navigation_pendentes_execucao():
    selector = SAMScraper._resolve_report_navigation("pendentes_execucao")
    assert selector.endswith("/SAM_SMA_Reports/PendingToExecution.aspx")


def test_resolve_report_navigation_consulta_ssa():
    selector = SAMScraper._resolve_report_navigation("consulta_ssa")
    assert selector.endswith("/SAM_SMA/SSASearch.aspx")


def test_resolve_report_navigation_consulta_ssa_print():
    selector = SAMScraper._resolve_report_navigation("consulta_ssa_print")
    assert selector.endswith("/SAM_SMA/SSASearch.aspx")


def test_resolve_report_navigation_aprovacao_emissao():
    selector = SAMScraper._resolve_report_navigation("aprovacao_emissao")
    assert selector.endswith("/SAM_SMA_Reports/SSAsPendingOfApprovalOnEmission.aspx")


def test_resolve_report_navigation_reprogramacoes():
    selector = SAMScraper._resolve_report_navigation("reprogramacoes")
    assert selector.endswith("/SAM_SMA_Reports/SSAsRescheduled.aspx")


def test_resolve_report_navigation_invalid():
    with pytest.raises(ValueError):
        SAMScraper._resolve_report_navigation("x")


def test_filter_contract_includes_emission_year_week_fields():
    assert "EmissionYearWeekStart_input" in SAMLocators.FILTER["emission_year_week_start"]
    assert "EmissionYearWeekEnd_input" in SAMLocators.FILTER["emission_year_week_end"]
    assert "SectorEmitter" in SAMLocators.FILTER["setor_emissor"]
    assert "DivisionEmmiter" in SAMLocators.FILTER["divisao_emissora"]
    assert "wtSearchButton" in SAMLocators.FILTER["search_icon"]
    assert "wtButtonDropdownWrapper" in SAMLocators.FILTER["actions_menu"]
    assert "dropdown-header.select" in SAMLocators.FILTER["actions_menu"]
    assert "wtLink_ExportToExcel" in SAMLocators.FILTER["export_excel"]
    assert "wtLink_ExportToPDF" in SAMLocators.FILTER["export_pdf"]
    assert "Nenhuma SSA encontrada para exibir" in SAMLocators.FILTER["no_results_message"]
