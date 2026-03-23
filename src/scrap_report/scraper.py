"""Scraper Playwright modular para extrair xlsx do SAM."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

import pandas as pd
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from .config import (
    EMISSION_DATE_SUPPORTED_REPORT_KINDS,
    ScrapeConfig,
    report_kind_runtime_filter_name,
    report_kind_supports_filter,
)
from .redaction import redact_text
from .selector_engine import (
    build_candidates,
    filter_candidates_for_mode,
    pick_best_available,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ScrapeResult:
    """Resultado da execucao do scraper."""

    report_kind: str
    downloaded_path: Path
    started_at: str
    finished_at: str


class SAMLocators:
    """Seletores centralizados."""

    LOGIN = {
        "username": "[name*='wtUsername'][name*='wtUserNameInput']",
        "password": "[name*='wtPassword'][name*='wtPasswordInput']",
        "submit": "[name*='wtAction'][type='submit']",
    }

    NAVIGATION = {
        "pendentes": "/SAM_SMA_Reports/PendingGeneralSSAs.aspx",
        "executadas": "/SAM_SMA_Reports/SSAsExecuted.aspx",
        "pendentes_execucao": "/SAM_SMA_Reports/PendingToExecution.aspx",
        "consulta_ssa": "/SAM_SMA/SSASearch.aspx",
        "consulta_ssa_print": "/SAM_SMA/SSASearch.aspx",
        "aprovacao_emissao": "/SAM_SMA_Reports/SSAsPendingOfApprovalOnEmission.aspx",
        "aprovacao_cancelamento": "/SAM_SMA_Reports/SSAsPendingOfApprovalForCancel.aspx",
        "derivadas_relacionadas": "/SAM_SMA_Reports/SSAsDerivatedAndRelated.aspx",
        "reprogramacoes": "/SAM_SMA_Reports/SSAsRescheduled.aspx",
    }

    FILTER = {
        "numero_ssa": "input[id*='SSADashboardFilter_SSANumber'], input[id*='SSANumber']",
        "emission_date": "input[id*='EmissionDate_input']",
        "emission_year_week_start": "input[id*='EmissionYearWeekStart_input']",
        "emission_year_week_end": "input[id*='EmissionYearWeekEnd_input']",
        "setor_emissor": "[id*='SectorEmitter']",
        "setor_executor": "[id*='SectorExecutor']",
        "divisao_emissora": "[id*='DivisionEmmiter']",
        "search_icon": "a[id$='wtSearchButton'], a[id*='wtSearchButton']",
        "search_button": "input[id$='wtSearch'][type='submit']:not([id*='SearchLocalization'])",
        "actions_menu": "div[id*='wtButtonDropdownWrapper'] > div.dropdown-header.select",
        "export_excel": "a[id*='wtLink_ExportToExcel']",
        "export_pdf": "a[id*='wtLink_ExportToPDF']",
        "consulta_results": "[id*='wtFinalPlaceholder_wtListSSAs'], [id*='wtListSSAs']",
        "consulta_result_link": "a[href*='SSAView.aspx?SSAId=']",
        "no_results_message": "text=Nenhuma SSA encontrada para exibir...",
    }


class SAMScraper:
    """Executa fluxo de scraping de relatorio."""

    EMPTY_RESULT_COLUMNS = (
        "Numero da SSA",
        "Situacao",
        "Derivada de",
        "Localizacao",
        "Descricao da Localizacao",
        "Equipamento",
        "Semana de Cadastro",
        "Emitida Em",
        "Descricao da SSA",
        "Setor Emissor",
        "Setor Executor",
        "Solicitante",
    )

    def __init__(self, config: ScrapeConfig):
        self.config = config
        self.locators = SAMLocators()

    def run(self) -> ScrapeResult:
        started_at = datetime.now().isoformat(timespec="seconds")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=self.config.headless)
            context = browser.new_context(
                accept_downloads=True,
                ignore_https_errors=self.config.ignore_https_errors,
            )
            page = context.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            page.set_default_timeout(self.config.loading_timeout_ms)

            try:
                self._login(page)
                self._navigate_to_report(page)
                self._wait_for_filter_field(page)
                self._fill_filter(page)
                no_results = self._click_search(page)
                if no_results:
                    downloaded = self._build_empty_result_download()
                    finished_at = datetime.now().isoformat(timespec="seconds")
                    return ScrapeResult(
                        report_kind=self.config.report_kind,
                        downloaded_path=downloaded,
                        started_at=started_at,
                        finished_at=finished_at,
                    )
                self._select_report_options(page)
                downloaded = self._export_download(page)
                finished_at = datetime.now().isoformat(timespec="seconds")
                return ScrapeResult(
                    report_kind=self.config.report_kind,
                    downloaded_path=downloaded,
                    started_at=started_at,
                    finished_at=finished_at,
                )
            finally:
                browser.close()

    def _safe_action(self, action: Callable[[], None], error_msg: str) -> None:
        for attempt in range(1, self.config.retry_attempts + 1):
            try:
                action()
                return
            except Exception as exc:
                safe_msg = redact_text(str(exc))
                logger.error(
                    "tentativa %s/%s: %s: %s",
                    attempt,
                    self.config.retry_attempts,
                    error_msg,
                    safe_msg,
                )
                if attempt >= self.config.retry_attempts:
                    raise
                time.sleep(2 ** (attempt - 1))

    def _login(self, page: Page) -> None:
        def action() -> None:
            page.goto(self.config.base_url)
            user_selector = self._resolve_selector(
                page,
                stable_id=self.locators.LOGIN["username"],
                name="[name*='UserName']",
            )
            pass_selector = self._resolve_selector(
                page,
                stable_id=self.locators.LOGIN["password"],
                name="[name*='Password']",
            )
            submit_selector = self._resolve_selector(
                page,
                stable_id=self.locators.LOGIN["submit"],
                text="text=Entrar",
                xpath="//button[@type='submit']",
            )
            page.fill(user_selector, self.config.username)
            page.fill(pass_selector, self.config.password)
            page.click(submit_selector)

        self._safe_action(action, "erro no login")

    def _navigate_to_report(self, page: Page) -> None:
        report_target = self._resolve_report_navigation(self.config.report_kind)

        def action() -> None:
            page.goto(self._build_report_url(report_target))
            self._wait_for_loading_complete(page, self.config.loading_timeout_ms)

        self._safe_action(action, "erro na navegacao")

    @staticmethod
    def _resolve_report_navigation(report_kind: str) -> str:
        if report_kind == "pendentes":
            return SAMLocators.NAVIGATION["pendentes"]
        if report_kind == "executadas":
            return SAMLocators.NAVIGATION["executadas"]
        if report_kind == "pendentes_execucao":
            return SAMLocators.NAVIGATION["pendentes_execucao"]
        if report_kind == "consulta_ssa":
            return SAMLocators.NAVIGATION["consulta_ssa"]
        if report_kind == "consulta_ssa_print":
            return SAMLocators.NAVIGATION["consulta_ssa_print"]
        if report_kind == "aprovacao_emissao":
            return SAMLocators.NAVIGATION["aprovacao_emissao"]
        if report_kind == "aprovacao_cancelamento":
            return SAMLocators.NAVIGATION["aprovacao_cancelamento"]
        if report_kind == "derivadas_relacionadas":
            return SAMLocators.NAVIGATION["derivadas_relacionadas"]
        if report_kind == "reprogramacoes":
            return SAMLocators.NAVIGATION["reprogramacoes"]
        raise ValueError("report_kind invalido")

    def _build_report_url(self, report_path: str) -> str:
        if report_path.startswith("http://") or report_path.startswith("https://"):
            return report_path
        parts = urlsplit(self.config.base_url)
        return f"{parts.scheme}://{parts.netloc}{report_path}"

    def _wait_for_filter_field(self, page: Page) -> None:
        selector = self._resolve_primary_filter_selector(page)
        page.wait_for_selector(
            selector,
            state="visible",
            timeout=self.config.navigation_timeout_ms,
        )

    def _fill_filter(self, page: Page) -> None:
        for filter_name in self._iter_requested_filters():
            self._apply_filter(page, filter_name)

    def _click_search(self, page: Page) -> bool:
        success = page.evaluate(
            """(args) => {
                const icon = document.querySelector(args.iconSelector);
                if (icon) {
                    icon.click();
                    return 'icon';
                }
                const fallback = document.querySelector(args.fallbackSelector);
                if (fallback) {
                    fallback.click();
                    return 'fallback';
                }
                return '';
            }""",
            {
                "iconSelector": self.locators.FILTER["search_icon"],
                "fallbackSelector": self.locators.FILTER["search_button"],
            },
        )
        if not success:
            raise RuntimeError("falha ao acionar busca principal")
        self._wait_for_search_results(page)
        return self._handle_no_results(page)

    def _select_report_options(self, page: Page) -> None:
        if self.config.report_kind in {"consulta_ssa", "consulta_ssa_print"}:
            return
        details_locator = page.locator("text=Relatorio com Detalhes")
        if details_locator.count() == 0:
            return
        details_locator.first.click()
        self._wait_for_loading_complete(page, self.config.loading_timeout_ms)

    def _export_download(self, page: Page) -> Path:
        selector = self._resolve_selector(
            page,
            stable_id=self._resolve_export_locator(),
        )
        try:
            with page.expect_download(timeout=self.config.download_timeout_ms) as download_promise:
                self._open_actions_menu(page)
                self._wait_for_export_ready(page, selector)
                page.click(selector)

                download = download_promise.value
                target = self.config.download_dir / download.suggested_filename
                download.save_as(str(target))
                logger.info("download concluido: %s", target)
                return target
        except PlaywrightTimeoutError as exc:
            if self.config.report_kind == "derivadas_relacionadas":
                raise RuntimeError(
                    "report_kind=derivadas_relacionadas nao entregou download no fluxo oficial; "
                    "tela segue especial por export instavel"
                ) from exc
            raise

    def _resolve_export_locator(self) -> str:
        if self.config.report_kind == "consulta_ssa_print":
            return self.locators.FILTER["export_pdf"]
        return self.locators.FILTER["export_excel"]

    def _open_actions_menu(self, page: Page) -> None:
        menu_selector = self._resolve_selector(
            page,
            stable_id=self.locators.FILTER["actions_menu"],
        )
        page.click(menu_selector, force=True)

    def _wait_for_export_ready(self, page: Page, export_selector: str) -> None:
        page.wait_for_function(
            """(cssSelector) => {
                const exportButton = document.querySelector(cssSelector);
                if (!exportButton) {
                    return false;
                }
                const style = window.getComputedStyle(exportButton);
                return style.visibility !== 'hidden' && style.pointerEvents !== 'none';
            }""",
            arg=export_selector,
            timeout=self.config.loading_timeout_ms,
        )

    def _wait_for_search_results(self, page: Page) -> None:
        started = time.time()
        saw_loading = False
        while (time.time() - started) * 1000 < self.config.loading_timeout_ms:
            loading_state = page.evaluate(
                """() => {
                    const loadingBar = document.querySelector('[id*="wtdivWait"]');
                    if (!loadingBar) {
                        return 'absent';
                    }
                    return window.getComputedStyle(loadingBar).display;
                }"""
            )
            if loading_state not in {"none", "absent"}:
                saw_loading = True
            if self._search_results_ready(page, saw_loading, loading_state):
                page.wait_for_timeout(500)
                return
            page.wait_for_timeout(500)
        snapshot = self._dom_snapshot(page)
        raise RuntimeError(f"resultado da busca nao estabilizou; snapshot={snapshot}")

    def _search_results_ready(self, page: Page, saw_loading: bool, loading_state: str) -> bool:
        if self._has_no_results_message(page):
            return not saw_loading or loading_state == "none"
        if self.config.report_kind in {"consulta_ssa", "consulta_ssa_print"}:
            cards_ready = page.locator(self.locators.FILTER["consulta_results"]).count() > 0
            links_ready = page.locator(self.locators.FILTER["consulta_result_link"]).count() > 0
            return (cards_ready or links_ready) and (not saw_loading or loading_state == "none")
        export_ready = page.locator(self.locators.FILTER["export_excel"]).count() > 0
        return export_ready and (not saw_loading or loading_state == "none")

    def _handle_no_results(self, page: Page) -> bool:
        if not self._has_no_results_message(page):
            return False
        if self._allow_empty_result_success():
            logger.info(
                "busca sem resultados para report_kind=%s; gerando artefato vazio sinalizado",
                self.config.report_kind,
            )
            return True
        raise RuntimeError("busca sem resultados para os filtros informados")

    def _has_no_results_message(self, page: Page) -> bool:
        return page.locator(self.locators.FILTER["no_results_message"]).count() > 0

    def _allow_empty_result_success(self) -> bool:
        return self.config.report_kind == "aprovacao_cancelamento"

    def _build_empty_result_download(self) -> Path:
        title = self._empty_result_title()
        rows = [[title], list(self.EMPTY_RESULT_COLUMNS)]
        placeholder = pd.DataFrame(rows)
        target = self.config.download_dir / self._empty_result_filename()
        with pd.ExcelWriter(target, engine="openpyxl") as writer:
            placeholder.to_excel(writer, index=False, header=False, sheet_name="Dados")
        return target

    def _empty_result_title(self) -> str:
        return (
            "Sem resultados para os filtros: "
            f"ssa={self.config.numero_ssa or 'ALL'}; "
            f"emissor={self.config.setor_emissor or 'ALL'}; "
            f"executor={self.config.setor_executor or 'ALL'}; "
            f"emissao={self._empty_result_emission_label()}"
        )

    def _resolve_primary_filter_selector(self, page: Page) -> str:
        for filter_name in self._iter_requested_filters():
            return self._resolve_filter_selector(page, filter_name)
        raise RuntimeError("nenhum filtro primario disponivel para a tela atual")

    def _iter_requested_filters(self) -> tuple[str, ...]:
        requested: list[str] = []
        if self.config.numero_ssa:
            requested.append("numero_ssa")
        if self.config.setor_emissor:
            requested.append("setor_emissor")
        if self.config.setor_executor:
            requested.append("setor_executor")
        if self._uses_emission_date_filter():
            requested.append("emission_date")
        else:
            requested.append("emission_year_week")
        return tuple(requested)

    def _apply_filter(self, page: Page, filter_name: str) -> None:
        if filter_name == "numero_ssa":
            selector = self._resolve_filter_selector(page, filter_name)
            page.fill(selector, self.config.numero_ssa)
            return
        if filter_name == "emission_date":
            selector = self._resolve_filter_selector(page, filter_name)
            if self.config.emission_date_start != self.config.emission_date_end:
                raise RuntimeError(
                    "tela atual suporta apenas data de emissao unica; inicio e fim devem ser iguais"
                )
            page.fill(selector, self.config.emission_date_start)
            return
        if filter_name == "emission_year_week":
            emission_start_selector = self._resolve_selector(
                page,
                stable_id=self.locators.FILTER["emission_year_week_start"],
                name="[name*='EmissionYearWeekStart']",
            )
            emission_end_selector = self._resolve_selector(
                page,
                stable_id=self.locators.FILTER["emission_year_week_end"],
                name="[name*='EmissionYearWeekEnd']",
            )
            page.fill(emission_start_selector, self.config.emission_year_week_start)
            page.fill(emission_end_selector, self.config.emission_year_week_end)
            return
        if filter_name == "setor_emissor":
            selector = self._resolve_filter_selector(page, filter_name)
            page.fill(selector, self.config.setor_emissor or "")
            return
        if filter_name == "setor_executor":
            selector = self._resolve_filter_selector(page, filter_name)
            page.fill(selector, self.config.setor_executor or "")
            return
        raise RuntimeError(f"filtro nao suportado internamente: {filter_name}")

    def _resolve_filter_selector(self, page: Page, filter_name: str) -> str:
        self._ensure_filter_supported(filter_name)
        if filter_name == "numero_ssa":
            return self._resolve_selector(
                page,
                stable_id=self.locators.FILTER["numero_ssa"],
                name="[name*='SSANumber']",
            )
        if filter_name == "emission_date":
            return self._resolve_emission_date_filter_selector(page)
        if filter_name == "emission_year_week":
            return self._resolve_selector(
                page,
                stable_id=self.locators.FILTER["emission_year_week_start"],
                name="[name*='EmissionYearWeekStart']",
            )
        if filter_name == "setor_emissor":
            return self._resolve_selector(
                page,
                stable_id=self.locators.FILTER["setor_emissor"],
                name="[name*='SectorEmitter']",
            )
        if filter_name == "setor_executor":
            return self._resolve_executor_filter_selector(page)
        raise RuntimeError(f"filtro sem seletor mapeado: {filter_name}")

    def _ensure_filter_supported(self, filter_name: str) -> None:
        if not report_kind_supports_filter(self.config.report_kind, filter_name):
            raise RuntimeError(
                f"report_kind={self.config.report_kind} nao suporta filtro {filter_name} validado"
            )

    def _uses_emission_date_filter(self) -> bool:
        return bool(self.config.emission_date_start or self.config.emission_date_end)

    def _resolve_emission_date_filter_selector(self, page: Page) -> str:
        if self.config.report_kind not in EMISSION_DATE_SUPPORTED_REPORT_KINDS:
            raise RuntimeError(
                f"report_kind={self.config.report_kind} nao suporta filtro por data de emissao validado"
            )
        try:
            return self._resolve_selector(
                page,
                stable_id=self.locators.FILTER["emission_date"],
                name="[name*='EmissionDate']",
            )
        except RuntimeError as exc:
            raise RuntimeError(
                f"report_kind={self.config.report_kind} nao expoe campo de data de emissao compativel"
            ) from exc

    def _empty_result_emission_label(self) -> str:
        if self._uses_emission_date_filter():
            return f"{self.config.emission_date_start}..{self.config.emission_date_end}"
        return f"{self.config.emission_year_week_start}..{self.config.emission_year_week_end}"

    def _resolve_executor_filter_selector(self, page: Page) -> str:
        runtime_filter = report_kind_runtime_filter_name(
            self.config.report_kind,
            "setor_executor",
        )
        if runtime_filter == "divisao_emissora":
            return self._resolve_selector(
                page,
                stable_id=self.locators.FILTER["divisao_emissora"],
                name="[name*='DivisionEmmiter']",
            )
        return self._resolve_selector(
            page,
            stable_id=self.locators.FILTER["setor_executor"],
            name="[name*='SectorExecutor']",
        )

    def _empty_result_filename(self) -> str:
        stem = f"{self.config.report_kind}_sem_resultados_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return f"{stem}.xlsx"

    def _wait_for_loading_complete(self, page: Page, timeout_ms: int) -> bool:
        started = time.time()
        while (time.time() - started) * 1000 < timeout_ms:
            loading_complete = page.evaluate(
                """() => {
                    const loadingBar = document.querySelector('[id*="wtdivWait"]');
                    if (loadingBar && window.getComputedStyle(loadingBar).display !== 'none') {
                        return false;
                    }
                    return true;
                }"""
            )
            if loading_complete:
                page.wait_for_load_state("networkidle", timeout=self.config.network_idle_timeout_ms)
                page.wait_for_timeout(1000)
                return True
            page.wait_for_timeout(1000)
        return False

    def _resolve_selector(
        self,
        page: Page,
        stable_id: str | None = None,
        name: str | None = None,
        aria_label: str | None = None,
        text: str | None = None,
        xpath: str | None = None,
    ) -> str:
        candidates = build_candidates(
            stable_id=stable_id,
            name=name,
            aria_label=aria_label,
            text=text,
            xpath=xpath,
        )
        candidates = filter_candidates_for_mode(candidates, self.config.selector_mode)
        if not candidates:
            raise RuntimeError("modo strict removeu todos os seletores candidatos")

        def is_available(selector: str) -> bool:
            if not self._dom_health_check(page):
                return False
            return page.locator(selector).count() > 0

        selected = pick_best_available(candidates, is_available)
        if selected is None:
            snapshot = self._dom_snapshot(page)
            raise RuntimeError(
                f"nenhum seletor valido encontrado; mode={self.config.selector_mode}; snapshot={snapshot}"
            )
        return selected.selector

    @staticmethod
    def _dom_health_check(page: Page) -> bool:
        state = page.evaluate("() => document.readyState")
        return state in {"interactive", "complete"}

    @staticmethod
    def _dom_snapshot(page: Page) -> str:
        state = page.evaluate("() => document.readyState")
        links = page.evaluate("() => document.querySelectorAll('a').length")
        inputs = page.evaluate("() => document.querySelectorAll('input').length")
        return f"ready={state},links={links},inputs={inputs}"
