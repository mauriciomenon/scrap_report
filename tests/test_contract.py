import scrap_report
import pytest

from scrap_report.contract import (
    CLI_ENTRYPOINT,
    EXPORT_CONTRACTS,
    IMPORT_NAME,
    MINIMUM_FIELDS_BY_FLOW,
    MODULE_ENTRYPOINT,
    PACKAGE_NAME,
    PACKAGE_VERSION,
    PREFERRED_CONTRACTS,
    PRODUCER,
    SCHEMA_REQUIRED_FIELDS,
    SCHEMA_VERSION,
    build_contract_catalog,
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
    assert PACKAGE_NAME == "scrap-report"
    assert PACKAGE_VERSION == "0.1.17"
    assert IMPORT_NAME == "scrap_report"
    assert CLI_ENTRYPOINT == "scrap-report"
    assert MODULE_ENTRYPOINT == "python -m scrap_report.cli"
    assert "playwright_reports" in EXPORT_CONTRACTS
    assert "rest_reports" in EXPORT_CONTRACTS
    assert EXPORT_CONTRACTS["playwright_reports"]["dados"] == "data_xlsx"
    assert EXPORT_CONTRACTS["rest_reports"]["csv"] == "data_csv"
    assert PREFERRED_CONTRACTS["sam_api"]["schema"] == "sam_api_result"
    assert PREFERRED_CONTRACTS["sweep_run_rest"]["schema"] == "sweep_result"
    assert MINIMUM_FIELDS_BY_FLOW["sam_api_flow"][0] == "status"
    assert "manifest_json" in MINIMUM_FIELDS_BY_FLOW["sam_api_standalone"]
    assert "contract_info" in SCHEMA_REQUIRED_FIELDS
    assert "sam_api_result" in SCHEMA_REQUIRED_FIELDS
    assert "sam_api_flow_result" in SCHEMA_REQUIRED_FIELDS
    assert "sweep_result" in SCHEMA_REQUIRED_FIELDS
    assert "filters" in SCHEMA_REQUIRED_FIELDS["sam_api_result"]
    assert "warnings" in SCHEMA_REQUIRED_FIELDS["sam_api_result"]
    assert "verify_tls" in SCHEMA_REQUIRED_FIELDS["sam_api_result"]
    assert "runtime_mode" in SCHEMA_REQUIRED_FIELDS["sam_api_result"]
    assert "telemetry" in SCHEMA_REQUIRED_FIELDS["sam_api_result"]
    assert "manifest_json" in SCHEMA_REQUIRED_FIELDS["sam_api_result"]
    assert "timeout_seconds" in SCHEMA_REQUIRED_FIELDS["sam_api_flow_result"]
    assert "runtime_mode" in SCHEMA_REQUIRED_FIELDS["sam_api_flow_result"]
    assert "telemetry" in SCHEMA_REQUIRED_FIELDS["sam_api_flow_result"]
    assert "manifest_json" in SCHEMA_REQUIRED_FIELDS["sam_api_flow_result"]
    assert "manifest_json" in SCHEMA_REQUIRED_FIELDS["sweep_result"]
    assert "runtime_mode" in SCHEMA_REQUIRED_FIELDS["sweep_result"]


def test_build_contract_catalog_exposes_package_metadata():
    catalog = build_contract_catalog()

    assert catalog["package"]["package_name"] == "scrap-report"
    assert catalog["package"]["package_version"] == "0.1.17"
    assert catalog["package"]["import_name"] == "scrap_report"
    assert catalog["package"]["cli_entrypoint"] == "scrap-report"
    assert catalog["package"]["module_entrypoint"] == "python -m scrap_report.cli"
    assert catalog["preferred_contracts"]["sam_api_flow"]["schema"] == "sam_api_result"


def test_public_package_surface_exposes_version_and_contract_helpers():
    assert scrap_report.__version__ == "0.1.17"
    assert scrap_report.PACKAGE_NAME == "scrap-report"
    assert scrap_report.PACKAGE_VERSION == "0.1.17"
    assert scrap_report.IMPORT_NAME == "scrap_report"
    assert callable(scrap_report.build_contract_catalog)
    assert "sam_api_flow" in scrap_report.MINIMUM_FIELDS_BY_FLOW


def test_validate_payload_schema_sam_api_result_ok():
    validate_payload_schema(
        "sam_api_result",
        {
            "status": "ok",
            "mode": "search",
            "runtime_mode": "rest",
            "count": 1,
            "items": [],
            "telemetry": {
                "record_count": 1,
                "detail_count": 0,
                "without_detail_count": 1,
            },
            "exports": {},
            "manifest_json": "tmp/sam-api.json",
            "filters": {},
            "warnings": [],
            "verify_tls": True,
            "timeout_seconds": 60,
        },
    )


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
