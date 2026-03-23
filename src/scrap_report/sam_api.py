"""Cliente HTTP e utilitarios para consultar a SAM_SMA_API sem Playwright."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
import re
import shutil
import ssl
import subprocess
from typing import Any, Iterable, Sequence
import urllib.error
from urllib.parse import urlencode
import urllib.request

from .config import normalize_emission_date

DEFAULT_SAM_API_BASE_URL = "https://apps.itaipu.gov.br/SAM_SMA_API/rest/SSA_API"
MAX_SAM_API_DETAIL_BATCH_SIZE = 500
SAM_API_EXPORT_COLUMNS = (
    "ssa_number",
    "localization",
    "description",
    "issue_datetime",
    "emission_datetime",
    "emitter_sector",
    "executor_sector",
    "year_week",
    "situation_desc",
    "process_status",
    "detail_present",
)


class SAMApiError(RuntimeError):
    """Erro funcional ao consultar a SAM_SMA_API."""


def _chunk_sequence(values: Sequence[str], chunk_size: int) -> tuple[tuple[str, ...], ...]:
    if chunk_size <= 0:
        raise ValueError("chunk_size deve ser maior que zero")
    return tuple(
        tuple(values[index : index + chunk_size]) for index in range(0, len(values), chunk_size)
    )


@dataclass(slots=True)
class SAMApiClient:
    base_url: str = DEFAULT_SAM_API_BASE_URL
    timeout_seconds: float = 30.0
    verify_tls: bool = True
    ca_file: str | None = None
    _detail_cache: dict[str, dict[str, Any]] = field(default_factory=dict, init=False, repr=False)

    def _build_url(self, endpoint: str, params: dict[str, Any]) -> str:
        normalized_base = self.base_url.rstrip("/")
        query = urlencode(params)
        return f"{normalized_base}/{endpoint}?{query}"

    def _build_ssl_context(self) -> ssl.SSLContext | None:
        if self.verify_tls:
            if self.ca_file:
                ca_path = Path(self.ca_file)
                if not ca_path.is_file():
                    raise SAMApiError(f"ca_file nao encontrado: {self.ca_file}")
                try:
                    return ssl.create_default_context(cafile=str(ca_path))
                except ssl.SSLError as exc:
                    raise SAMApiError(f"ca_file invalido: {self.ca_file}: {exc}") from exc
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
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, ssl.SSLCertVerificationError):
                detail = getattr(reason, "verify_message", None) or str(reason)
                raise SAMApiError(
                    f"falha ao consultar {endpoint}: TLS nao confiavel ({detail}); "
                    "forneca --ca-file ou use --ignore-https-errors quando permitido"
                ) from exc
            if isinstance(reason, ssl.SSLError):
                raise SAMApiError(f"falha ao consultar {endpoint}: erro TLS ({reason})") from exc
            raise SAMApiError(f"falha ao consultar {endpoint}: {exc}") from exc
        except ssl.SSLCertVerificationError as exc:
            detail = getattr(exc, "verify_message", None) or str(exc)
            raise SAMApiError(
                f"falha ao consultar {endpoint}: TLS nao confiavel ({detail}); "
                "forneca --ca-file ou use --ignore-https-errors quando permitido"
            ) from exc
        except ssl.SSLError as exc:
            raise SAMApiError(f"falha ao consultar {endpoint}: erro TLS ({exc})") from exc
        except Exception as exc:  # pragma: no cover - depende da rede
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
        cached = self._detail_cache.get(normalized_number)
        if cached is not None:
            return cached
        payload = self._request_json(
            "GetSSABySSANumber",
            {"SSANumber": normalized_number},
        )
        if not isinstance(payload, dict):
            raise SAMApiError("GetSSABySSANumber nao retornou objeto")
        self._detail_cache[normalized_number] = payload
        return payload

    def get_ssas_by_numbers(self, ssa_numbers: Sequence[str]) -> list[dict[str, Any]]:
        unique_numbers: list[str] = []
        seen: set[str] = set()
        for value in ssa_numbers:
            normalized = value.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique_numbers.append(normalized)
        return [self.get_ssa_by_number(ssa_number) for ssa_number in unique_numbers]


def _normalize_text(value: object) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    return text or None


def _normalize_upper_set(values: Iterable[str]) -> set[str]:
    return {value.strip().upper() for value in values if value and value.strip()}


def _normalize_ssa_number_set(values: Iterable[str]) -> set[str]:
    return {value.strip() for value in values if value and value.strip()}


def _normalize_ssa_number_list(values: Iterable[str]) -> list[str]:
    unique_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip() if value else ""
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_values.append(normalized)
    return unique_values


def _extract_pem_blocks(text: str) -> list[str]:
    return re.findall(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", text, flags=re.S)


def _extract_chain_metadata(text: str) -> list[tuple[str, str]]:
    metadata: list[tuple[str, str]] = []
    lines = text.splitlines()
    for index, line in enumerate(lines[:-1]):
        subject_match = re.match(r"\s*\d+\s+s:(.*)", line)
        issuer_match = re.match(r"\s*i:(.*)", lines[index + 1])
        if not subject_match or not issuer_match:
            continue
        metadata.append((subject_match.group(1).strip(), issuer_match.group(1).strip()))
    return metadata


def export_server_root_ca(
    output_path: str | Path,
    host: str = "apps.itaipu.gov.br",
    port: int = 443,
    openssl_bin: str | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    resolved_openssl = openssl_bin or shutil.which("openssl")
    if not resolved_openssl:
        raise SAMApiError("openssl nao encontrado no PATH para exportar a cadeia do servidor")
    command = [
        resolved_openssl,
        "s_client",
        "-showcerts",
        "-servername",
        host,
        "-connect",
        f"{host}:{port}",
    ]
    try:
        completed = subprocess.run(
            command,
            input="Q\n",
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SAMApiError(f"timeout ao consultar cadeia TLS de {host}:{port}") from exc
    output = completed.stdout or ""
    if not output:
        stderr = (completed.stderr or "").strip()
        raise SAMApiError(f"openssl nao retornou cadeia TLS para {host}:{port}: {stderr or 'saida vazia'}")

    pem_blocks = _extract_pem_blocks(output)
    if not pem_blocks:
        raise SAMApiError(f"nenhum certificado PEM encontrado na cadeia TLS de {host}:{port}")

    metadata = _extract_chain_metadata(output)
    root_index = len(pem_blocks) - 1
    subject = issuer = None
    if metadata:
        for index, (chain_subject, chain_issuer) in enumerate(metadata[: len(pem_blocks)]):
            if chain_subject == chain_issuer:
                root_index = index
                subject = chain_subject
                issuer = chain_issuer
                break
        if subject is None or issuer is None:
            subject, issuer = metadata[min(root_index, len(metadata) - 1)]

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(pem_blocks[root_index] + "\n", encoding="utf-8")
    return {
        "host": host,
        "port": port,
        "output_path": str(target),
        "openssl_bin": resolved_openssl,
        "certificate_count": len(pem_blocks),
        "root_certificate_index": root_index,
        "subject": subject,
        "issuer": issuer,
    }


def _parse_datetime_value(value: object) -> datetime | None:
    text = _normalize_text(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _coerce_year_week(value: object) -> int | None:
    text = _normalize_text(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    return int(digits)


def _derive_year_week_from_datetime_text(value: object) -> int | None:
    parsed = _parse_datetime_value(value)
    if parsed is None:
        return None
    iso_year, iso_week, _ = parsed.isocalendar()
    return (iso_year * 100) + iso_week


def normalize_ssa_record(
    base_record: dict[str, Any] | None = None,
    detail_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = base_record or {}
    detail = detail_record or {}
    ssa_number = _normalize_text(
        detail.get("SSANumber") or base.get("SSANumber") or base.get("ssa_number")
    )
    issue_datetime = _normalize_text(
        detail.get("IssueDateTime") or base.get("IssueDateTime") or base.get("issue_datetime")
    )
    emission_datetime = _normalize_text(detail.get("EmissionDateTime"))
    year_week = _coerce_year_week(detail.get("YearWeek") or base.get("year_week"))
    if year_week is None:
        year_week = _derive_year_week_from_datetime_text(
            detail.get("IssueDateTime") or base.get("IssueDateTime") or base.get("issue_datetime")
        )
    record = {
        "ssa_number": ssa_number,
        "localization": _normalize_text(
            detail.get("LocalizationCode")
            or base.get("Localization")
            or detail.get("LocalizationCodeOld")
            or base.get("localization")
        ),
        "description": _normalize_text(
            detail.get("Description") or base.get("Description") or base.get("description")
        ),
        "issue_datetime": issue_datetime,
        "emission_datetime": emission_datetime or _normalize_text(base.get("emission_datetime")),
        "emitter_sector": _normalize_text(
            detail.get("EmmiterSector") or base.get("EmitterSector") or base.get("emitter_sector")
        ),
        "executor_sector": _normalize_text(
            detail.get("ExecutorSector") or base.get("ExecutorSector") or base.get("executor_sector")
        ),
        "year_week": year_week,
        "situation_desc": _normalize_text(detail.get("SituationDesc") or base.get("situation_desc")),
        "process_status": _normalize_text(detail.get("ProcessStatus") or base.get("process_status")),
        "detail_present": bool(detail_record),
    }
    return record


def filter_normalized_ssa_records(
    records: Sequence[dict[str, Any]],
    executor_sectors: Sequence[str] = (),
    emitter_sectors: Sequence[str] = (),
    localization_contains: str | None = None,
    ssa_numbers: Sequence[str] = (),
    year_week_start: str | None = None,
    year_week_end: str | None = None,
    emission_date_start: str | None = None,
    emission_date_end: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    executor_filter = _normalize_upper_set(executor_sectors)
    emitter_filter = _normalize_upper_set(emitter_sectors)
    ssa_filter = _normalize_ssa_number_set(ssa_numbers)
    localization_filter = (localization_contains or "").strip().upper()

    normalized_emission_start = normalize_emission_date(emission_date_start)
    normalized_emission_end = normalize_emission_date(emission_date_end)
    start_emission_date = (
        datetime.strptime(normalized_emission_start, "%d/%m/%Y").date()
        if normalized_emission_start
        else None
    )
    end_emission_date = (
        datetime.strptime(normalized_emission_end, "%d/%m/%Y").date()
        if normalized_emission_end
        else None
    )
    start_year_week = int(year_week_start) if year_week_start else None
    end_year_week = int(year_week_end) if year_week_end else None

    filtered: list[dict[str, Any]] = []
    for record in records:
        executor_value = str(record.get("executor_sector") or "").strip().upper()
        emitter_value = str(record.get("emitter_sector") or "").strip().upper()
        localization_value = str(record.get("localization") or "").strip().upper()
        ssa_value = str(record.get("ssa_number") or "").strip()

        if executor_filter and executor_value not in executor_filter:
            continue
        if emitter_filter and emitter_value not in emitter_filter:
            continue
        if localization_filter and localization_filter not in localization_value:
            continue
        if ssa_filter and ssa_value not in ssa_filter:
            continue

        year_week_value = record.get("year_week")
        if start_year_week is not None:
            if year_week_value is None or int(year_week_value) < start_year_week:
                continue
        if end_year_week is not None:
            if year_week_value is None or int(year_week_value) > end_year_week:
                continue

        emission_value = _parse_datetime_value(record.get("emission_datetime"))
        if start_emission_date is not None:
            if emission_value is None or emission_value.date() < start_emission_date:
                continue
        if end_emission_date is not None:
            if emission_value is None or emission_value.date() > end_emission_date:
                continue

        filtered.append(record)
        if limit is not None and len(filtered) >= limit:
            break
    return filtered


def _prefilter_base_records_by_year_week(
    records: Sequence[dict[str, Any]],
    year_week_start: str | None = None,
    year_week_end: str | None = None,
) -> list[dict[str, Any]]:
    if not year_week_start and not year_week_end:
        return list(records)
    start_year_week = int(year_week_start) if year_week_start else None
    end_year_week = int(year_week_end) if year_week_end else None
    filtered: list[dict[str, Any]] = []
    for record in records:
        year_week_value = record.get("year_week")
        if year_week_value is None:
            filtered.append(record)
            continue
        numeric_year_week = int(year_week_value)
        if start_year_week is not None and numeric_year_week < start_year_week:
            continue
        if end_year_week is not None and numeric_year_week > end_year_week:
            continue
        filtered.append(record)
    return filtered


def fetch_ssa_details_by_numbers(
    client: SAMApiClient,
    ssa_numbers: Sequence[str],
    executor_sectors: Sequence[str] = (),
    emitter_sectors: Sequence[str] = (),
    localization_contains: str | None = None,
    year_week_start: str | None = None,
    year_week_end: str | None = None,
    emission_date_start: str | None = None,
    emission_date_end: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    normalized_numbers = _normalize_ssa_number_list(ssa_numbers)
    raw_details: list[dict[str, Any]] = []
    for chunk in _chunk_sequence(tuple(normalized_numbers), MAX_SAM_API_DETAIL_BATCH_SIZE):
        raw_details.extend(client.get_ssas_by_numbers(chunk))
    records = [normalize_ssa_record(detail_record=item) for item in raw_details]
    return filter_normalized_ssa_records(
        records,
        executor_sectors=executor_sectors,
        emitter_sectors=emitter_sectors,
        localization_contains=localization_contains,
        ssa_numbers=normalized_numbers,
        year_week_start=year_week_start,
        year_week_end=year_week_end,
        emission_date_start=emission_date_start,
        emission_date_end=emission_date_end,
        limit=limit,
    )


def query_sam_api_records(
    client: SAMApiClient,
    ssa_numbers: Sequence[str] = (),
    executor_sectors: Sequence[str] = (),
    emitter_sectors: Sequence[str] = (),
    start_localization_code: str = "A000A000",
    end_localization_code: str = "Z999Z999",
    number_of_years: int = 100000,
    include_details: bool = False,
    localization_contains: str | None = None,
    year_week_start: str | None = None,
    year_week_end: str | None = None,
    emission_date_start: str | None = None,
    emission_date_end: str | None = None,
    limit: int | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    normalized_numbers = _normalize_ssa_number_list(ssa_numbers)
    if normalized_numbers:
        return (
            "detail",
            fetch_ssa_details_by_numbers(
                client=client,
                ssa_numbers=normalized_numbers,
                executor_sectors=executor_sectors,
                emitter_sectors=emitter_sectors,
                localization_contains=localization_contains,
                year_week_start=year_week_start,
                year_week_end=year_week_end,
                emission_date_start=emission_date_start,
                emission_date_end=emission_date_end,
                limit=limit,
            ),
        )
    return (
        "search",
        search_pending_ssas_by_localization_range(
            client=client,
            executor_sectors=executor_sectors,
            emitter_sectors=emitter_sectors,
            start_localization_code=start_localization_code,
            end_localization_code=end_localization_code,
            number_of_years=number_of_years,
            include_details=include_details,
            localization_contains=localization_contains,
            year_week_start=year_week_start,
            year_week_end=year_week_end,
            emission_date_start=emission_date_start,
            emission_date_end=emission_date_end,
            limit=limit,
        ),
    )


def build_sam_api_summary(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    by_executor: dict[str, int] = {}
    by_emitter: dict[str, int] = {}
    by_year_week: dict[str, int] = {}
    detail_count = 0
    for record in records:
        executor = str(record.get("executor_sector") or "").strip() or "UNKNOWN"
        emitter = str(record.get("emitter_sector") or "").strip() or "UNKNOWN"
        year_week = str(record.get("year_week") or "").strip() or "UNKNOWN"
        by_executor[executor] = by_executor.get(executor, 0) + 1
        by_emitter[emitter] = by_emitter.get(emitter, 0) + 1
        by_year_week[year_week] = by_year_week.get(year_week, 0) + 1
        if bool(record.get("detail_present")):
            detail_count += 1
    return {
        "total": len(records),
        "detail_count": detail_count,
        "without_detail_count": len(records) - detail_count,
        "by_executor": dict(sorted(by_executor.items())),
        "by_emitter": dict(sorted(by_emitter.items())),
        "by_year_week": dict(sorted(by_year_week.items())),
    }


def search_pending_ssas_by_localization_range(
    client: SAMApiClient,
    executor_sectors: Sequence[str] = (),
    emitter_sectors: Sequence[str] = (),
    start_localization_code: str = "A000A000",
    end_localization_code: str = "Z999Z999",
    number_of_years: int = 100000,
    include_details: bool = False,
    localization_contains: str | None = None,
    ssa_numbers: Sequence[str] = (),
    year_week_start: str | None = None,
    year_week_end: str | None = None,
    emission_date_start: str | None = None,
    emission_date_end: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    pending = client.get_pending_ssas_by_localization_range(
        start_localization_code=start_localization_code,
        end_localization_code=end_localization_code,
        number_of_years=number_of_years,
    )
    base_records = [normalize_ssa_record(base_record=item) for item in pending]
    detail_filter_requested = bool(
        year_week_start or year_week_end or emission_date_start or emission_date_end
    )
    needs_details = include_details or detail_filter_requested
    base_filtered = filter_normalized_ssa_records(
        base_records,
        executor_sectors=executor_sectors,
        emitter_sectors=emitter_sectors,
        localization_contains=localization_contains,
        ssa_numbers=ssa_numbers,
        limit=None if detail_filter_requested else limit,
    )
    if detail_filter_requested:
        base_filtered = _prefilter_base_records_by_year_week(
            base_filtered,
            year_week_start=year_week_start,
            year_week_end=year_week_end,
        )
    if not needs_details:
        return base_filtered

    raw_ssa_numbers_for_detail = [str(item.get("ssa_number") or "").strip() for item in base_filtered]
    if any(not value for value in raw_ssa_numbers_for_detail):
        raise SAMApiError("item retornado sem ssa_number, impossivel enriquecer com detalhe")
    ssa_numbers_for_detail = _normalize_ssa_number_list(raw_ssa_numbers_for_detail)
    detail_records: list[dict[str, Any]] = []
    for chunk in _chunk_sequence(tuple(ssa_numbers_for_detail), MAX_SAM_API_DETAIL_BATCH_SIZE):
        detail_records.extend(client.get_ssas_by_numbers(chunk))
    detail_by_number = {
        str(item.get("SSANumber") or "").strip(): item for item in detail_records if item.get("SSANumber")
    }
    merged_records = [
        normalize_ssa_record(
            base_record=item,
            detail_record=detail_by_number.get(str(item.get("ssa_number") or "").strip()),
        )
        for item in base_filtered
    ]
    return filter_normalized_ssa_records(
        merged_records,
        executor_sectors=executor_sectors,
        emitter_sectors=emitter_sectors,
        localization_contains=localization_contains,
        ssa_numbers=ssa_numbers,
        year_week_start=year_week_start,
        year_week_end=year_week_end,
        emission_date_start=emission_date_start,
        emission_date_end=emission_date_end,
        limit=limit,
    )
