"""Cliente HTTP minimo para consultar a SAM_SMA_API sem Playwright."""

from __future__ import annotations

from dataclasses import dataclass
import json
import ssl
from typing import Any
from urllib.parse import urlencode
import urllib.request

DEFAULT_SAM_API_BASE_URL = "https://apps.itaipu.gov.br/SAM_SMA_API/rest/SSA_API"


class SAMApiError(RuntimeError):
    """Erro funcional ao consultar a SAM_SMA_API."""


@dataclass(slots=True)
class SAMApiClient:
    base_url: str = DEFAULT_SAM_API_BASE_URL
    timeout_seconds: float = 30.0
    verify_tls: bool = True

    def _build_url(self, endpoint: str, params: dict[str, Any]) -> str:
        normalized_base = self.base_url.rstrip("/")
        query = urlencode(params)
        return f"{normalized_base}/{endpoint}?{query}"

    def _build_ssl_context(self) -> ssl.SSLContext | None:
        if self.verify_tls:
            return None
        return ssl._create_unverified_context()

    def _request_json(self, endpoint: str, params: dict[str, Any]) -> Any:
        url = self._build_url(endpoint, params)
        request = urllib.request.Request(url, method="GET")
        context = self._build_ssl_context()
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
                context=context,
            ) as response:
                body = response.read().decode("utf-8")
        except Exception as exc:  # pragma: no cover - network errors depend on runtime
            raise SAMApiError(f"falha ao consultar {endpoint}: {exc}") from exc
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise SAMApiError(f"resposta invalida de {endpoint}: json malformado") from exc

    def get_pending_ssas_by_localization_range(
        self,
        start_localization_code: str,
        end_localization_code: str,
        number_of_years: int,
    ) -> list[dict[str, Any]]:
        payload = self._request_json(
            "GetPendingSSAsByLocalizationRange",
            {
                "StartLocalizationCode": start_localization_code,
                "EndLocalizationCode": end_localization_code,
                "NumberOfYears": number_of_years,
            },
        )
        if not isinstance(payload, list):
            raise SAMApiError("GetPendingSSAsByLocalizationRange nao retornou lista")
        return [item for item in payload if isinstance(item, dict)]

    def get_ssa_by_number(self, ssa_number: str) -> dict[str, Any]:
        normalized_number = ssa_number.strip()
        if not normalized_number:
            raise ValueError("ssa_number nao pode ser vazio")
        payload = self._request_json(
            "GetSSABySSANumber",
            {"SSANumber": normalized_number},
        )
        if not isinstance(payload, dict):
            raise SAMApiError("GetSSABySSANumber nao retornou objeto")
        return payload


def search_pending_ssas_by_localization_range(
    client: SAMApiClient,
    executor_sectors: tuple[str, ...] = (),
    start_localization_code: str = "A000A000",
    end_localization_code: str = "Z999Z999",
    number_of_years: int = 100000,
    include_details: bool = False,
) -> list[dict[str, Any]]:
    pending = client.get_pending_ssas_by_localization_range(
        start_localization_code=start_localization_code,
        end_localization_code=end_localization_code,
        number_of_years=number_of_years,
    )
    normalized_sectors = {sector.strip().upper() for sector in executor_sectors if sector.strip()}
    if normalized_sectors:
        pending = [
            item
            for item in pending
            if str(item.get("ExecutorSector", "")).strip().upper() in normalized_sectors
        ]
    if not include_details:
        return pending

    detailed_items: list[dict[str, Any]] = []
    for item in pending:
        ssa_number = str(item.get("SSANumber", "")).strip()
        if not ssa_number:
            raise SAMApiError("item retornado sem SSANumber, impossivel detalhar")
        detail = client.get_ssa_by_number(ssa_number)
        merged = dict(item)
        merged["detail"] = detail
        detailed_items.append(merged)
    return detailed_items
