import pytest

from scrap_report.contract import (
    PRODUCER,
    SCHEMA_REQUIRED_FIELDS,
    SCHEMA_VERSION,
    utc_now_iso,
    validate_contract_definition,
    validate_payload_schema,
)


def test_validate_contract_definition_ok():
    validate_contract_definition()


def test_validate_payload_schema_missing_field():
    with pytest.raises(ValueError):
        validate_payload_schema("stage_result", {"status": "ok"})


def test_validate_payload_schema_unknown_schema():
    with pytest.raises(ValueError):
        validate_payload_schema("unknown", {"status": "ok"})


def test_contract_constants_present():
    assert SCHEMA_VERSION == "1.0.0"
    assert PRODUCER == "scrap_report.cli"
    assert "contract_info" in SCHEMA_REQUIRED_FIELDS
    assert "sam_api_result" in SCHEMA_REQUIRED_FIELDS
    assert "sam_api_flow_result" in SCHEMA_REQUIRED_FIELDS
    assert "sweep_result" in SCHEMA_REQUIRED_FIELDS
    assert "filters" in SCHEMA_REQUIRED_FIELDS["sam_api_result"]
    assert "warnings" in SCHEMA_REQUIRED_FIELDS["sam_api_result"]
    assert "verify_tls" in SCHEMA_REQUIRED_FIELDS["sam_api_result"]
    assert "timeout_seconds" in SCHEMA_REQUIRED_FIELDS["sam_api_flow_result"]
    assert "manifest_json" in SCHEMA_REQUIRED_FIELDS["sweep_result"]
    assert "runtime_mode" in SCHEMA_REQUIRED_FIELDS["sweep_result"]


def test_validate_payload_schema_sweep_result_ok():
    validate_payload_schema(
        "sweep_result",
        {
            "status": "ok",
            "report_kind": "pendentes",
            "scope_mode": "emissor",
            "runtime_mode": "rest",
            "item_count": 1,
            "success_count": 1,
            "failure_count": 0,
            "items": [],
            "manifest_json": "tmp/sweep.json",
        },
    )


def test_utc_now_iso_format():
    value = utc_now_iso()
    assert value.endswith("Z")
    assert "T" in value
