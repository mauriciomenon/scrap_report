import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from scrap_report.config import ScrapeConfig
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


def test_resolve_report_navigation_aprovacao_cancelamento():
    selector = SAMScraper._resolve_report_navigation("aprovacao_cancelamento")
    assert selector.endswith("/SAM_SMA_Reports/SSAsPendingOfApprovalForCancel.aspx")


def test_resolve_report_navigation_derivadas_relacionadas():
    selector = SAMScraper._resolve_report_navigation("derivadas_relacionadas")
    assert selector.endswith("/SAM_SMA_Reports/SSAsDerivatedAndRelated.aspx")


def test_resolve_report_navigation_reprogramacoes():
    selector = SAMScraper._resolve_report_navigation("reprogramacoes")
    assert selector.endswith("/SAM_SMA_Reports/SSAsRescheduled.aspx")


def test_resolve_report_navigation_invalid():
    with pytest.raises(ValueError):
        SAMScraper._resolve_report_navigation("x")


def test_filter_contract_includes_emission_year_week_fields():
    assert "SSADashboardFilter_SSANumber" in SAMLocators.FILTER["numero_ssa"]
    assert "EmissionDate_input" in SAMLocators.FILTER["emission_date"]
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


def test_allow_empty_result_success_only_for_aprovacao_cancelamento(tmp_path):
    cfg_cancel = ScrapeConfig(
        username="u",
        password="p",
        setor_emissor="IEE3",
        setor_executor="MEL4",
        report_kind="aprovacao_cancelamento",
        download_dir=tmp_path / "downloads1",
        staging_dir=tmp_path / "staging1",
    )
    cfg_pend = ScrapeConfig(
        username="u",
        password="p",
        setor_emissor="IEE3",
        setor_executor="MEL4",
        report_kind="pendentes",
        download_dir=tmp_path / "downloads2",
        staging_dir=tmp_path / "staging2",
    )

    assert SAMScraper(cfg_cancel)._allow_empty_result_success() is True
    assert SAMScraper(cfg_pend)._allow_empty_result_success() is False


def test_build_empty_result_download_creates_header_only_xlsx(tmp_path):
    cfg = ScrapeConfig(
        username="u",
        password="p",
        setor_emissor="IEE3",
        setor_executor="MEL4",
        report_kind="aprovacao_cancelamento",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
    )
    scraper = SAMScraper(cfg)
    path = scraper._build_empty_result_download()

    assert path.exists()
    assert path.suffix.lower() == ".xlsx"
    assert "sem_resultados" in path.name


def test_derivadas_relacionadas_export_timeout_has_explicit_runtime_error(tmp_path, monkeypatch):
    cfg = ScrapeConfig(
        username="u",
        password="p",
        setor_emissor="IEE3",
        setor_executor="MEL4",
        report_kind="derivadas_relacionadas",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
    )
    scraper = SAMScraper(cfg)

    class FakeDownloadPromise:
        @property
        def value(self):
            raise PlaywrightTimeoutError("timed out")

    class FakeExpectDownload:
        def __enter__(self):
            return FakeDownloadPromise()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakePage:
        def expect_download(self, timeout):
            return FakeExpectDownload()

        def click(self, selector):
            return None

    monkeypatch.setattr(scraper, "_resolve_selector", lambda *args, **kwargs: "selector-ok")
    monkeypatch.setattr(scraper, "_open_actions_menu", lambda page: None)
    monkeypatch.setattr(scraper, "_wait_for_export_ready", lambda page, selector: None)

    with pytest.raises(RuntimeError, match="tela segue especial por export instavel"):
        scraper._export_download(FakePage())


def test_empty_result_title_uses_all_when_filters_are_disabled(tmp_path):
    cfg = ScrapeConfig(
        username="u",
        password="p",
        setor_emissor="ALL",
        setor_executor="ALL",
        report_kind="aprovacao_cancelamento",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
    )

    title = SAMScraper(cfg)._empty_result_title()

    assert "emissor=ALL" in title
    assert "executor=ALL" in title


def test_empty_result_title_uses_emission_date_when_configured(tmp_path):
    cfg = ScrapeConfig(
        username="u",
        password="p",
        setor_emissor="OUO5",
        setor_executor="ALL",
        report_kind="executadas",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
        emission_date_start="25/12/2025",
        emission_date_end="25/12/2025",
    )

    title = SAMScraper(cfg)._empty_result_title()

    assert "emissao=25/12/2025..25/12/2025" in title


def test_primary_filter_prefers_emission_date_when_active(tmp_path):
    cfg = ScrapeConfig(
        username="u",
        password="p",
        setor_emissor="OUO5",
        setor_executor="ALL",
        report_kind="executadas",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
        emission_date_start="25/12/2025",
        emission_date_end="25/12/2025",
    )

    assert SAMScraper(cfg)._uses_emission_date_filter() is True


def test_pending_orders_setor_before_emission_date(tmp_path):
    cfg = ScrapeConfig(
        username="u",
        password="p",
        setor_emissor="OUO5",
        setor_executor="ALL",
        report_kind="pendentes",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
        emission_date_start="25/12/2025",
        emission_date_end="25/12/2025",
    )

    assert SAMScraper(cfg)._iter_requested_filters() == ("setor_emissor", "emission_date")


def test_primary_filter_prefers_numero_ssa_when_active(tmp_path):
    cfg = ScrapeConfig(
        username="u",
        password="p",
        setor_emissor="ALL",
        setor_executor="ALL",
        numero_ssa="202603879",
        report_kind="consulta_ssa",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
    )

    assert SAMScraper(cfg)._iter_requested_filters()[0] == "numero_ssa"


def test_consulta_ssa_keeps_numero_ssa_before_emission_date(tmp_path):
    cfg = ScrapeConfig(
        username="u",
        password="p",
        setor_emissor="ALL",
        setor_executor="ALL",
        numero_ssa="202602521",
        report_kind="consulta_ssa",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
        emission_date_start="23/02/2026",
        emission_date_end="23/02/2026",
    )

    assert SAMScraper(cfg)._iter_requested_filters() == ("numero_ssa", "emission_date")


def test_unsupported_report_kind_rejects_emission_date_selector(tmp_path):
    cfg = ScrapeConfig(
        username="u",
        password="p",
        setor_emissor="OUO5",
        setor_executor="ALL",
        report_kind="aprovacao_emissao",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
        emission_date_start="25/12/2025",
        emission_date_end="25/12/2025",
    )

    with pytest.raises(
        RuntimeError,
        match="nao suporta filtro por data de emissao validado; export atual nao entrega Emitida Em confiavel",
    ):
        SAMScraper(cfg)._resolve_emission_date_filter_selector(page=None)  # type: ignore[arg-type]


def test_unsupported_report_kind_rejects_numero_ssa_selector(tmp_path):
    cfg = ScrapeConfig(
        username="u",
        password="p",
        setor_emissor="ALL",
        setor_executor="ALL",
        numero_ssa="202603879",
        report_kind="pendentes",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
    )

    with pytest.raises(RuntimeError, match="nao suporta filtro numero_ssa validado"):
        SAMScraper(cfg)._resolve_filter_selector(page=None, filter_name="numero_ssa")  # type: ignore[arg-type]


def test_aprovacao_emissao_accepts_numero_ssa_selector(tmp_path, monkeypatch):
    cfg = ScrapeConfig(
        username="u",
        password="p",
        setor_emissor="ALL",
        setor_executor="ALL",
        numero_ssa="202604340",
        report_kind="aprovacao_emissao",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
    )
    seen: dict[str, str] = {}

    def fake_resolve_selector(self, page, stable_id=None, name=None, **kwargs):
        seen["stable_id"] = stable_id or ""
        seen["name"] = name or ""
        return "selector-ok"

    monkeypatch.setattr(SAMScraper, "_resolve_selector", fake_resolve_selector)

    selector = SAMScraper(cfg)._resolve_filter_selector(page=None, filter_name="numero_ssa")  # type: ignore[arg-type]

    assert selector == "selector-ok"
    assert seen["stable_id"] == SAMLocators.FILTER["numero_ssa"]
    assert seen["name"] == "[name*='SSANumber']"


def test_aprovacao_emissao_maps_executor_filter_to_divisao_emissora(tmp_path, monkeypatch):
    cfg = ScrapeConfig(
        username="u",
        password="p",
        setor_emissor="IEE3",
        setor_executor="MEL4",
        report_kind="aprovacao_emissao",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
    )
    seen: dict[str, str] = {}

    def fake_resolve_selector(self, page, stable_id=None, name=None, **kwargs):
        seen["stable_id"] = stable_id or ""
        seen["name"] = name or ""
        return "selector-ok"

    monkeypatch.setattr(SAMScraper, "_resolve_selector", fake_resolve_selector)

    selector = SAMScraper(cfg)._resolve_executor_filter_selector(page=None)  # type: ignore[arg-type]

    assert selector == "selector-ok"
    assert seen["stable_id"] == SAMLocators.FILTER["divisao_emissora"]
    assert seen["name"] == "[name*='DivisionEmmiter']"
