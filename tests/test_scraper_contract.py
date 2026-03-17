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


def test_resolve_report_navigation_invalid():
    with pytest.raises(ValueError):
        SAMScraper._resolve_report_navigation("x")


def test_filter_contract_includes_emission_year_week_fields():
    assert "EmissionYearWeekStart_input" in SAMLocators.FILTER["emission_year_week_start"]
    assert "EmissionYearWeekEnd_input" in SAMLocators.FILTER["emission_year_week_end"]
    assert "SectorEmitter" in SAMLocators.FILTER["setor_emissor"]
    assert "wtSearchButton" in SAMLocators.FILTER["search_icon"]
    assert "wtButtonDropdownWrapper" in SAMLocators.FILTER["actions_menu"]
    assert "dropdown-header.select" in SAMLocators.FILTER["actions_menu"]
    assert "wtLink_ExportToExcel" in SAMLocators.FILTER["export_excel"]
