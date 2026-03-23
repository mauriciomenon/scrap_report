from __future__ import annotations

import json
from pathlib import Path
import ssl
import subprocess
import urllib.error
from urllib.parse import parse_qs, urlparse

import pytest

from scrap_report.sam_api import (
    MAX_SAM_API_DETAIL_BATCH_SIZE,
    SAMApiClient,
    SAMApiError,
    build_sam_api_summary,
    export_server_root_ca,
    fetch_ssa_details_by_numbers,
    filter_normalized_ssa_records,
    normalize_ssa_record,
    query_sam_api_records,
    search_pending_ssas_by_localization_range,
)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_get_pending_ssas_by_localization_range_builds_query(monkeypatch: pytest.MonkeyPatch):
    seen = {}

    def fake_urlopen(request, timeout, context):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["has_context"] = context is not None
        return _FakeResponse(
            [
                {
                    "SSANumber": "202600001",
                    "ExecutorSector": "MEL4",
                }
            ]
        )

    monkeypatch.setattr("scrap_report.sam_api.urllib.request.urlopen", fake_urlopen)

    client = SAMApiClient(timeout_seconds=12.5, verify_tls=False)
    items = client.get_pending_ssas_by_localization_range("A000A000", "Z999Z999", 7)

    assert items == [{"SSANumber": "202600001", "ExecutorSector": "MEL4"}]
    parsed = urlparse(seen["url"])
    params = parse_qs(parsed.query)
    assert parsed.path.endswith("/GetPendingSSAsByLocalizationRange")
    assert params["StartLocalizationCode"] == ["A000A000"]
    assert params["EndLocalizationCode"] == ["Z999Z999"]
    assert params["NumberOfYears"] == ["7"]
    assert seen["timeout"] == 12.5
    assert seen["has_context"] is True


def test_get_ssa_by_number_requires_non_empty_value():
    client = SAMApiClient()

    with pytest.raises(ValueError):
        client.get_ssa_by_number("   ")


def test_get_ssa_by_number_uses_client_cache(monkeypatch: pytest.MonkeyPatch):
    client = SAMApiClient()
    seen = {"count": 0}

    def fake_request_json(self, endpoint, params):
        seen["count"] += 1
        return {"SSANumber": params["SSANumber"], "ExecutorSector": "MEL4"}

    monkeypatch.setattr(SAMApiClient, "_request_json", fake_request_json)

    first = client.get_ssa_by_number("202602521")
    second = client.get_ssa_by_number("202602521")

    assert first["SSANumber"] == "202602521"
    assert second["SSANumber"] == "202602521"
    assert seen["count"] == 1


def test_normalize_ssa_record_merges_base_and_detail():
    record = normalize_ssa_record(
        base_record={
            "SSANumber": "202600001",
            "Localization": "B016M005",
            "Description": "Base",
            "IssueDateTime": "2026-01-01T06:00:00Z",
            "EmitterSector": "OUO6",
            "ExecutorSector": "MAM1",
        },
        detail_record={
            "SSANumber": "202600001",
            "LocalizationCode": "B016M005",
            "Description": "Detalhe",
            "EmmiterSector": "IEE3",
            "ExecutorSector": "MEL4",
            "EmissionDateTime": "23/02/2026 10:52:02",
            "YearWeek": 202609,
            "SituationDesc": "AGUARDANDO PROGRAMACAO",
            "ProcessStatus": "SSA Planejada",
        },
    )

    assert record["ssa_number"] == "202600001"
    assert record["description"] == "Detalhe"
    assert record["emitter_sector"] == "IEE3"
    assert record["executor_sector"] == "MEL4"
    assert record["year_week"] == 202609
    assert record["detail_present"] is True


def test_normalize_ssa_record_derives_year_week_from_issue_datetime():
    record = normalize_ssa_record(
        base_record={
            "SSANumber": "202600001",
            "IssueDateTime": "2026-01-01T06:00:00Z",
        }
    )

    assert record["year_week"] == 202601


def test_filter_normalized_ssa_records_supports_emitter_executor_and_limit():
    records = [
        {"ssa_number": "1", "emitter_sector": "IEE3", "executor_sector": "MEL4", "localization": "A", "year_week": 202609, "emission_datetime": "23/02/2026 10:52:02"},
        {"ssa_number": "2", "emitter_sector": "IEE1", "executor_sector": "MEL4", "localization": "B", "year_week": 202610, "emission_datetime": "24/02/2026 10:52:02"},
        {"ssa_number": "3", "emitter_sector": "IEE3", "executor_sector": "MEL3", "localization": "C", "year_week": 202611, "emission_datetime": "25/02/2026 10:52:02"},
    ]

    filtered = filter_normalized_ssa_records(
        records,
        executor_sectors=("MEL4",),
        emitter_sectors=("IEE3", "IEE1"),
        year_week_start="202609",
        year_week_end="202610",
        emission_date_start="2026-02-23",
        emission_date_end="24/02/2026",
        limit=1,
    )

    assert len(filtered) == 1
    assert filtered[0]["ssa_number"] == "1"


def test_fetch_ssa_details_by_numbers_filters_and_limits(monkeypatch: pytest.MonkeyPatch):
    client = SAMApiClient()
    monkeypatch.setattr(
        SAMApiClient,
        "get_ssas_by_numbers",
        lambda self, ssa_numbers: [
            {
                "SSANumber": number,
                "LocalizationCode": f"L{index}",
                "Description": f"SSA {number}",
                "EmmiterSector": "IEE3" if index == 0 else "IEE1",
                "ExecutorSector": "MEL4",
                "EmissionDateTime": "23/02/2026 10:52:02",
                "YearWeek": 202609 + index,
            }
            for index, number in enumerate(ssa_numbers)
        ],
    )

    records = fetch_ssa_details_by_numbers(
        client,
        ssa_numbers=("202600001", "202600002"),
        emitter_sectors=("IEE3",),
        year_week_end="202609",
        limit=1,
    )

    assert len(records) == 1
    assert records[0]["ssa_number"] == "202600001"


def test_fetch_ssa_details_by_numbers_chunks_large_batch(monkeypatch: pytest.MonkeyPatch):
    client = SAMApiClient()
    seen_chunks: list[tuple[str, ...]] = []

    def fake_get_ssas_by_numbers(self, ssa_numbers):
        seen_chunks.append(tuple(ssa_numbers))
        return [
            {
                "SSANumber": number,
                "LocalizationCode": f"L{number}",
                "Description": f"SSA {number}",
                "EmmiterSector": "IEE3",
                "ExecutorSector": "MEL4",
                "EmissionDateTime": "23/02/2026 10:52:02",
                "YearWeek": 202609,
            }
            for number in ssa_numbers
        ]

    monkeypatch.setattr(SAMApiClient, "get_ssas_by_numbers", fake_get_ssas_by_numbers)

    records = fetch_ssa_details_by_numbers(
        client,
        ssa_numbers=tuple(str(index) for index in range(MAX_SAM_API_DETAIL_BATCH_SIZE + 1)),
    )

    assert len(records) == MAX_SAM_API_DETAIL_BATCH_SIZE + 1
    assert len(seen_chunks) == 2
    assert len(seen_chunks[0]) == MAX_SAM_API_DETAIL_BATCH_SIZE
    assert len(seen_chunks[1]) == 1
    assert records[0]["ssa_number"] == "0"


def test_fetch_ssa_details_by_numbers_dedupes_repeated_numbers(monkeypatch: pytest.MonkeyPatch):
    client = SAMApiClient()
    seen_chunks: list[tuple[str, ...]] = []

    def fake_get_ssas_by_numbers(self, ssa_numbers):
        seen_chunks.append(tuple(ssa_numbers))
        return [
            {
                "SSANumber": number,
                "LocalizationCode": f"L{number}",
                "Description": f"SSA {number}",
                "EmmiterSector": "IEE3",
                "ExecutorSector": "MEL4",
                "EmissionDateTime": "23/02/2026 10:52:02",
                "YearWeek": 202609,
            }
            for number in ssa_numbers
        ]

    monkeypatch.setattr(SAMApiClient, "get_ssas_by_numbers", fake_get_ssas_by_numbers)

    records = fetch_ssa_details_by_numbers(
        client,
        ssa_numbers=("202600001", "202600001", "202600002", "202600001"),
    )

    assert len(seen_chunks) == 1
    assert seen_chunks[0] == ("202600001", "202600002")
    assert [item["ssa_number"] for item in records] == ["202600001", "202600002"]


def test_query_sam_api_records_uses_detail_path(monkeypatch: pytest.MonkeyPatch):
    client = SAMApiClient()
    monkeypatch.setattr(
        "scrap_report.sam_api.fetch_ssa_details_by_numbers",
        lambda **kwargs: [{"ssa_number": "202602521"}],
    )

    mode, records = query_sam_api_records(client, ssa_numbers=("202602521",))

    assert mode == "detail"
    assert records == [{"ssa_number": "202602521"}]


def test_build_sam_api_summary_counts_records():
    summary = build_sam_api_summary(
        [
            {"executor_sector": "MEL4", "emitter_sector": "IEE3", "year_week": 202609, "detail_present": True},
            {"executor_sector": "MEL4", "emitter_sector": "IEE1", "year_week": 202609, "detail_present": False},
        ]
    )

    assert summary["total"] == 2
    assert summary["detail_count"] == 1
    assert summary["by_executor"]["MEL4"] == 2


def test_search_pending_ssas_filters_executor_and_merges_detail(monkeypatch: pytest.MonkeyPatch):
    client = SAMApiClient()
    monkeypatch.setattr(
        SAMApiClient,
        "get_pending_ssas_by_localization_range",
        lambda self, **_kwargs: [
            {"SSANumber": "202600001", "ExecutorSector": "MEL4", "EmitterSector": "IEE3", "Localization": "A001"},
            {"SSANumber": "202600002", "ExecutorSector": "MEL3", "EmitterSector": "IEE1", "Localization": "B002"},
        ],
    )
    monkeypatch.setattr(
        SAMApiClient,
        "get_ssas_by_numbers",
        lambda self, ssa_numbers: [
            {
                "SSANumber": number,
                "LocalizationCode": "A001",
                "Description": f"SSA {number}",
                "EmmiterSector": "IEE3",
                "ExecutorSector": "MEL4",
                "EmissionDateTime": "23/02/2026 10:52:02",
                "YearWeek": 202609,
            }
            for number in ssa_numbers
        ],
    )

    items = search_pending_ssas_by_localization_range(
        client,
        executor_sectors=("mel4",),
        include_details=True,
        localization_contains="a0",
    )

    assert len(items) == 1
    assert items[0]["ssa_number"] == "202600001"
    assert items[0]["detail_present"] is True


def test_search_pending_ssas_requires_ssa_number_when_detailing(monkeypatch: pytest.MonkeyPatch):
    client = SAMApiClient()
    monkeypatch.setattr(
        SAMApiClient,
        "get_pending_ssas_by_localization_range",
        lambda self, **_kwargs: [{"ExecutorSector": "MEL4"}],
    )
    monkeypatch.setattr(SAMApiClient, "get_ssas_by_numbers", lambda self, ssa_numbers: [])

    with pytest.raises(SAMApiError):
        search_pending_ssas_by_localization_range(client, include_details=True)


def test_search_pending_ssas_applies_detail_only_filters(monkeypatch: pytest.MonkeyPatch):
    client = SAMApiClient()
    monkeypatch.setattr(
        SAMApiClient,
        "get_pending_ssas_by_localization_range",
        lambda self, **_kwargs: [
            {"SSANumber": "202600001", "ExecutorSector": "MEL4", "EmitterSector": "IEE3", "Localization": "A001"},
            {"SSANumber": "202600002", "ExecutorSector": "MEL4", "EmitterSector": "IEE3", "Localization": "A002"},
        ],
    )
    monkeypatch.setattr(
        SAMApiClient,
        "get_ssas_by_numbers",
        lambda self, ssa_numbers: [
            {
                "SSANumber": "202600001",
                "ExecutorSector": "MEL4",
                "EmmiterSector": "IEE3",
                "LocalizationCode": "A001",
                "EmissionDateTime": "23/02/2026 10:52:02",
                "YearWeek": 202609,
            },
            {
                "SSANumber": "202600002",
                "ExecutorSector": "MEL4",
                "EmmiterSector": "IEE3",
                "LocalizationCode": "A002",
                "EmissionDateTime": "25/02/2026 10:52:02",
                "YearWeek": 202611,
            },
        ],
    )

    items = search_pending_ssas_by_localization_range(
        client,
        include_details=True,
        year_week_start="202610",
        emission_date_start="2026-02-24",
        emission_date_end="2026-02-25",
    )

    assert len(items) == 1
    assert items[0]["ssa_number"] == "202600002"


def test_search_pending_ssas_prefilters_by_derived_year_week_before_detail(
    monkeypatch: pytest.MonkeyPatch,
):
    client = SAMApiClient()
    seen = {}
    monkeypatch.setattr(
        SAMApiClient,
        "get_pending_ssas_by_localization_range",
        lambda self, **_kwargs: [
            {
                "SSANumber": "202600001",
                "ExecutorSector": "MEL4",
                "EmitterSector": "IEE3",
                "Localization": "A001",
                "IssueDateTime": "2026-01-01T06:00:00Z",
            },
            {
                "SSANumber": "202602521",
                "ExecutorSector": "MEL4",
                "EmitterSector": "IEE3",
                "Localization": "A002",
                "IssueDateTime": "23/02/2026 10:49:00",
            },
        ],
    )
    monkeypatch.setattr(
        SAMApiClient,
        "get_ssas_by_numbers",
        lambda self, ssa_numbers: (
            seen.update({"ssa_numbers": tuple(ssa_numbers)})
            or [
                {
                    "SSANumber": number,
                    "ExecutorSector": "MEL4",
                    "EmmiterSector": "IEE3",
                    "LocalizationCode": "A002",
                    "EmissionDateTime": "23/02/2026 10:52:02",
                    "YearWeek": 202609,
                }
                for number in ssa_numbers
            ]
        ),
    )

    items = search_pending_ssas_by_localization_range(
        client,
        include_details=True,
        year_week_start="202609",
        year_week_end="202609",
    )

    assert len(items) == 1
    assert items[0]["ssa_number"] == "202602521"
    assert seen["ssa_numbers"] == ("202602521",)


def test_search_pending_ssas_prefilters_by_emission_date_end_before_detail(
    monkeypatch: pytest.MonkeyPatch,
):
    client = SAMApiClient()
    seen = {}
    monkeypatch.setattr(
        SAMApiClient,
        "get_pending_ssas_by_localization_range",
        lambda self, **_kwargs: [
            {
                "SSANumber": "202600001",
                "ExecutorSector": "MEL4",
                "EmitterSector": "IEE3",
                "Localization": "A001",
                "IssueDateTime": "2026-02-23T06:00:00Z",
            },
            {
                "SSANumber": "202600002",
                "ExecutorSector": "MEL4",
                "EmitterSector": "IEE3",
                "Localization": "A002",
                "IssueDateTime": "2026-03-10T06:00:00Z",
            },
            {
                "SSANumber": "202600003",
                "ExecutorSector": "MEL4",
                "EmitterSector": "IEE3",
                "Localization": "A003",
            },
        ],
    )
    monkeypatch.setattr(
        SAMApiClient,
        "get_ssas_by_numbers",
        lambda self, ssa_numbers: (
            seen.update({"ssa_numbers": tuple(ssa_numbers)})
            or [
                {
                    "SSANumber": number,
                    "ExecutorSector": "MEL4",
                    "EmmiterSector": "IEE3",
                    "LocalizationCode": f"A{index + 1:03d}",
                    "EmissionDateTime": "23/02/2026 10:52:02",
                    "YearWeek": 202608,
                }
                for index, number in enumerate(ssa_numbers)
            ]
        ),
    )

    items = search_pending_ssas_by_localization_range(
        client,
        include_details=True,
        emission_date_start="2026-02-23",
        emission_date_end="2026-02-23",
    )

    assert seen["ssa_numbers"] == ("202600001", "202600003")
    assert [item["ssa_number"] for item in items] == ["202600001", "202600003"]


def test_search_pending_ssas_applies_limit_before_detail_when_only_include_details(
    monkeypatch: pytest.MonkeyPatch,
):
    client = SAMApiClient()
    seen = {}
    monkeypatch.setattr(
        SAMApiClient,
        "get_pending_ssas_by_localization_range",
        lambda self, **_kwargs: [
            {"SSANumber": "202600001", "ExecutorSector": "MEL4", "EmitterSector": "IEE3", "Localization": "A001"},
            {"SSANumber": "202600002", "ExecutorSector": "MEL4", "EmitterSector": "IEE3", "Localization": "A002"},
        ],
    )
    monkeypatch.setattr(
        SAMApiClient,
        "get_ssas_by_numbers",
        lambda self, ssa_numbers: (
            seen.update({"ssa_numbers": tuple(ssa_numbers)})
            or [
                {
                    "SSANumber": number,
                    "ExecutorSector": "MEL4",
                    "EmmiterSector": "IEE3",
                    "LocalizationCode": "A001",
                    "EmissionDateTime": "23/02/2026 10:52:02",
                    "YearWeek": 202609,
                }
                for number in ssa_numbers
            ]
        ),
    )

    items = search_pending_ssas_by_localization_range(
        client,
        include_details=True,
        limit=1,
    )

    assert len(items) == 1
    assert seen["ssa_numbers"] == ("202600001",)


def test_search_pending_ssas_chunks_large_enrichment_batch(monkeypatch: pytest.MonkeyPatch):
    client = SAMApiClient()
    seen_chunks: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        SAMApiClient,
        "get_pending_ssas_by_localization_range",
        lambda self, **_kwargs: [
            {"SSANumber": str(index), "ExecutorSector": "MEL4", "EmitterSector": "IEE3", "Localization": "A001"}
            for index in range(MAX_SAM_API_DETAIL_BATCH_SIZE + 1)
        ],
    )
    monkeypatch.setattr(
        SAMApiClient,
        "get_ssas_by_numbers",
        lambda self, ssa_numbers: (
            seen_chunks.append(tuple(ssa_numbers))
            or [
                {
                    "SSANumber": number,
                    "ExecutorSector": "MEL4",
                    "EmmiterSector": "IEE3",
                    "LocalizationCode": "A001",
                    "EmissionDateTime": "23/02/2026 10:52:02",
                    "YearWeek": 202609,
                }
                for number in ssa_numbers
            ]
        ),
    )

    items = search_pending_ssas_by_localization_range(client, include_details=True)

    assert len(items) == MAX_SAM_API_DETAIL_BATCH_SIZE + 1
    assert len(seen_chunks) == 2
    assert len(seen_chunks[0]) == MAX_SAM_API_DETAIL_BATCH_SIZE
    assert len(seen_chunks[1]) == 1


def test_search_pending_ssas_dedupes_repeated_ssa_detail_lookup(monkeypatch: pytest.MonkeyPatch):
    client = SAMApiClient()
    seen_chunks: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        SAMApiClient,
        "get_pending_ssas_by_localization_range",
        lambda self, **_kwargs: [
            {"SSANumber": "202600001", "ExecutorSector": "MEL4", "EmitterSector": "IEE3", "Localization": "A001"},
            {"SSANumber": "202600001", "ExecutorSector": "MEL4", "EmitterSector": "IEE3", "Localization": "A001"},
            {"SSANumber": "202600002", "ExecutorSector": "MEL4", "EmitterSector": "IEE3", "Localization": "A002"},
        ],
    )
    monkeypatch.setattr(
        SAMApiClient,
        "get_ssas_by_numbers",
        lambda self, ssa_numbers: (
            seen_chunks.append(tuple(ssa_numbers))
            or [
                {
                    "SSANumber": number,
                    "ExecutorSector": "MEL4",
                    "EmmiterSector": "IEE3",
                    "LocalizationCode": "A001" if number == "202600001" else "A002",
                    "EmissionDateTime": "23/02/2026 10:52:02",
                    "YearWeek": 202609,
                }
                for number in ssa_numbers
            ]
        ),
    )

    items = search_pending_ssas_by_localization_range(client, include_details=True)

    assert len(seen_chunks) == 1
    assert seen_chunks[0] == ("202600001", "202600002")
    assert len(items) == 3


def test_get_pending_ssas_by_localization_range_rejects_non_list(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "scrap_report.sam_api.urllib.request.urlopen",
        lambda request, timeout, context: _FakeResponse({"status": "not-list"}),
    )
    client = SAMApiClient()

    with pytest.raises(SAMApiError):
        client.get_pending_ssas_by_localization_range("A", "Z", 1)


def test_build_ssl_context_uses_custom_ca_file(tmp_path, monkeypatch: pytest.MonkeyPatch):
    seen = {}
    ca_file = tmp_path / "corp-ca.pem"
    ca_file.write_text("dummy", encoding="utf-8")

    def fake_create_default_context(*, cafile=None):
        seen["cafile"] = cafile
        return object()

    monkeypatch.setattr("scrap_report.sam_api.ssl.create_default_context", fake_create_default_context)

    client = SAMApiClient(verify_tls=True, ca_file=str(ca_file))
    context = client._build_ssl_context()

    assert context is not None
    assert seen["cafile"] == str(ca_file)


def test_build_ssl_context_rejects_missing_ca_file(tmp_path):
    client = SAMApiClient(verify_tls=True, ca_file=str(tmp_path / "missing.pem"))

    with pytest.raises(SAMApiError, match="ca_file nao encontrado"):
        client._build_ssl_context()


def test_export_server_root_ca_writes_self_signed_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    output = tmp_path / "root.pem"
    chain = """CONNECTED(00000004)
Certificate chain
 0 s:CN=Leaf
   i:CN=Root
-----BEGIN CERTIFICATE-----
LEAF
-----END CERTIFICATE-----
 1 s:CN=Root
   i:CN=Root
-----BEGIN CERTIFICATE-----
ROOT
-----END CERTIFICATE-----
"""

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout=chain, stderr="")

    monkeypatch.setattr("scrap_report.sam_api.shutil.which", lambda name: "openssl")
    monkeypatch.setattr("scrap_report.sam_api.subprocess.run", fake_run)

    payload = export_server_root_ca(output)

    assert output.read_text(encoding="utf-8") == "-----BEGIN CERTIFICATE-----\nROOT\n-----END CERTIFICATE-----\n"
    assert payload["root_certificate_index"] == 1
    assert payload["subject"] == "CN=Root"
    assert payload["issuer"] == "CN=Root"


def test_request_json_reports_tls_verification_error(monkeypatch: pytest.MonkeyPatch):
    def fake_urlopen(request, timeout, context):
        raise ssl.SSLCertVerificationError(1, "self-signed certificate in certificate chain")

    monkeypatch.setattr("scrap_report.sam_api.urllib.request.urlopen", fake_urlopen)

    client = SAMApiClient()

    with pytest.raises(SAMApiError, match="TLS nao confiavel"):
        client.get_ssa_by_number("202602521")


def test_request_json_reports_wrapped_tls_verification_error(monkeypatch: pytest.MonkeyPatch):
    def fake_urlopen(request, timeout, context):
        raise urllib.error.URLError(
            ssl.SSLCertVerificationError(1, "self-signed certificate in certificate chain")
        )

    monkeypatch.setattr("scrap_report.sam_api.urllib.request.urlopen", fake_urlopen)

    client = SAMApiClient()

    with pytest.raises(SAMApiError, match="TLS nao confiavel"):
        client.get_ssa_by_number("202602521")
