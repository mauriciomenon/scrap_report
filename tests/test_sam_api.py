from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import pytest

from scrap_report.sam_api import SAMApiClient, SAMApiError, search_pending_ssas_by_localization_range


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


def test_search_pending_ssas_filters_executor_and_merges_detail(monkeypatch: pytest.MonkeyPatch):
    client = SAMApiClient()
    monkeypatch.setattr(
        SAMApiClient,
        "get_pending_ssas_by_localization_range",
        lambda self, **_kwargs: [
            {"SSANumber": "202600001", "ExecutorSector": "MEL4"},
            {"SSANumber": "202600002", "ExecutorSector": "MEL3"},
        ],
    )
    monkeypatch.setattr(
        SAMApiClient,
        "get_ssa_by_number",
        lambda self, ssa_number: {"SSANumber": ssa_number, "SituationDesc": "OK"},
    )

    items = search_pending_ssas_by_localization_range(
        client,
        executor_sectors=("mel4",),
        include_details=True,
    )

    assert len(items) == 1
    assert items[0]["SSANumber"] == "202600001"
    assert items[0]["detail"]["SituationDesc"] == "OK"


def test_search_pending_ssas_requires_ssa_number_when_detailing(monkeypatch: pytest.MonkeyPatch):
    client = SAMApiClient()
    monkeypatch.setattr(
        SAMApiClient,
        "get_pending_ssas_by_localization_range",
        lambda self, **_kwargs: [{"ExecutorSector": "MEL4"}],
    )

    with pytest.raises(SAMApiError):
        search_pending_ssas_by_localization_range(client, include_details=True)
