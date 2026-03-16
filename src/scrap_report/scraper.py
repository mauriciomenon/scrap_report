"""Scraper Playwright modular para extrair xlsx do SAM."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from playwright.sync_api import Page, sync_playwright

from .config import ScrapeConfig
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
    }

    FILTER = {
        "setor_executor": "[id*='SectorExecutor']",
        "search_button": "input[id$='wtSearch'][type='submit']:not([id*='SearchLocalization'])",
        "export_excel": "a[id*='ExportToExcel']",
    }


class SAMScraper:
    """Executa fluxo de scraping de relatorio."""

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
                self._click_search(page)
                self._select_report_options(page)
                downloaded = self._export_to_excel(page)
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
        raise ValueError("report_kind invalido")

    def _build_report_url(self, report_path: str) -> str:
        if report_path.startswith("http://") or report_path.startswith("https://"):
            return report_path
        parts = urlsplit(self.config.base_url)
        return f"{parts.scheme}://{parts.netloc}{report_path}"

    def _wait_for_filter_field(self, page: Page) -> None:
        selector = self._resolve_selector(
            page,
            stable_id=self.locators.FILTER["setor_executor"],
            name="[name*='SectorExecutor']",
        )
        page.wait_for_selector(
            selector,
            state="visible",
            timeout=self.config.navigation_timeout_ms,
        )

    def _fill_filter(self, page: Page) -> None:
        selector = self._resolve_selector(
            page,
            stable_id=self.locators.FILTER["setor_executor"],
            name="[name*='SectorExecutor']",
        )
        page.fill(selector, self.config.setor_executor)

    def _click_search(self, page: Page) -> None:
        selector = self._resolve_selector(
            page,
            stable_id=self.locators.FILTER["search_button"],
        )
        success = page.evaluate(
            """(cssSelector) => {
                const element = document.querySelector(cssSelector);
                if (!element) {
                    return false;
                }
                element.click();
                return true;
            }""",
            selector,
        )
        if not success:
            raise RuntimeError("falha ao acionar busca principal")
        self._wait_for_loading_complete(page, self.config.loading_timeout_ms)

    def _select_report_options(self, page: Page) -> None:
        details_locator = page.locator("text=Relatorio com Detalhes")
        if details_locator.count() == 0:
            return
        details_locator.first.click()
        self._wait_for_loading_complete(page, self.config.loading_timeout_ms)

    def _export_to_excel(self, page: Page) -> Path:
        selector = self._resolve_selector(
            page,
            stable_id=self.locators.FILTER["export_excel"],
        )
        with page.expect_download(timeout=self.config.download_timeout_ms) as download_promise:
            success = page.evaluate(
                """(cssSelector) => {
                    const exportButton = document.querySelector(cssSelector);
                    if (!exportButton) {
                        return false;
                    }
                    exportButton.click();
                    return true;
                }""",
                selector,
            )
            if not success:
                raise RuntimeError("nao foi possivel acionar exportacao para excel")

            download = download_promise.value
            target = self.config.download_dir / download.suggested_filename
            download.save_as(str(target))
            logger.info("download concluido: %s", target)
            return target

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
