import pytest

from scrap_report.scraper import SAMScraper


def test_resolve_report_navigation_pendentes():
    selector = SAMScraper._resolve_report_navigation("pendentes")
    assert selector.endswith("/SAM_SMA_Reports/PendingGeneralSSAs.aspx")


def test_resolve_report_navigation_executadas():
    selector = SAMScraper._resolve_report_navigation("executadas")
    assert selector.endswith("/SAM_SMA_Reports/SSAsExecuted.aspx")


def test_resolve_report_navigation_invalid():
    with pytest.raises(ValueError):
        SAMScraper._resolve_report_navigation("x")
