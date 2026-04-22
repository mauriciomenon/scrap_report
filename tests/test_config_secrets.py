import pytest

from pathlib import Path

from datetime import date

from scrap_report.config import (
    CliConfigInput,
    CUSTOM_REPORT_PARSER_KINDS,
    FILTER_RUNTIME_ALIASES,
    ScrapeConfig,
    VALIDATED_FILTER_CAPABILITIES,
    SETOR_PRIORITY_GROUPS,
    build_recent_emission_year_week_window,
    normalize_emission_date,
    normalize_setor_filter,
    report_kind_runtime_filter_name,
    report_kind_uses_custom_parser,
)
from scrap_report.secret_provider import MemorySecretProvider


def test_normalize_setor_filter_accepts_all_tokens():
    assert normalize_setor_filter("ALL") is None
    assert normalize_setor_filter("*") is None
    assert normalize_setor_filter("") is None
    assert normalize_setor_filter("  iee3  ") == "IEE3"


def test_setor_priority_groups_keep_expected_order():
    assert SETOR_PRIORITY_GROUPS["principal"] == ("IEE3", "MEL4", "MEL3")
    assert SETOR_PRIORITY_GROUPS["segundo_plano"] == ("IEE1", "IEE2", "IEE4")
    assert SETOR_PRIORITY_GROUPS["terceiro_plano"] == (
        "MEL1",
        "MEL2",
        "IEQ1",
        "IEQ2",
        "IEQ3",
        "ILA1",
        "ILA2",
        "ILA3",
    )
    assert SETOR_PRIORITY_GROUPS["demais"] == ()


def test_validated_filter_capabilities_keep_consulta_numero_ssa():
    assert "numero_ssa" in VALIDATED_FILTER_CAPABILITIES["consulta_ssa"]
    assert "numero_ssa" in VALIDATED_FILTER_CAPABILITIES["consulta_ssa_print"]
    assert "numero_ssa" in VALIDATED_FILTER_CAPABILITIES["aprovacao_emissao"]
    assert "emission_date" in VALIDATED_FILTER_CAPABILITIES["consulta_ssa"]
    assert "emission_date" in VALIDATED_FILTER_CAPABILITIES["consulta_ssa_print"]
    assert "numero_ssa" not in VALIDATED_FILTER_CAPABILITIES["pendentes"]
    assert "emission_date" in VALIDATED_FILTER_CAPABILITIES["pendentes"]
    assert "emission_date" in VALIDATED_FILTER_CAPABILITIES["pendentes_execucao"]
    assert "emission_date" in VALIDATED_FILTER_CAPABILITIES["aprovacao_cancelamento"]
    assert "emission_date" in VALIDATED_FILTER_CAPABILITIES["reprogramacoes"]
    assert "emission_date" not in VALIDATED_FILTER_CAPABILITIES["aprovacao_emissao"]
    assert "emission_date" not in VALIDATED_FILTER_CAPABILITIES["derivadas_relacionadas"]


def test_runtime_filter_aliases_make_aprovacao_emissao_exception_explicit():
    assert FILTER_RUNTIME_ALIASES["aprovacao_emissao"]["setor_executor"] == "divisao_emissora"
    assert report_kind_runtime_filter_name("aprovacao_emissao", "setor_executor") == "divisao_emissora"
    assert report_kind_runtime_filter_name("pendentes", "setor_executor") == "setor_executor"


def test_custom_report_parser_kinds_make_derivadas_exception_explicit():
    assert CUSTOM_REPORT_PARSER_KINDS == ("derivadas_relacionadas",)
    assert report_kind_uses_custom_parser("derivadas_relacionadas") is True
    assert report_kind_uses_custom_parser("pendentes") is False


def test_cli_config_uses_provider_secret():
    provider = MemorySecretProvider()
    provider.set_secret("svc", "user1", "p1")
    cfg = CliConfigInput(
        username="user1",
        password=None,
        setor_emissor="IEE3",
        setor_executor="IEE3",
        report_kind="pendentes",
        base_url="https://osprd.itaipu/SAM_SMA/",
        headless=True,
        download_dir="downloads",
        staging_dir="staging",
        secure_required=True,
        allow_transitional_plaintext=False,
        secret_service="svc",
        secret_provider=provider,
    ).to_scrape_config()
    assert cfg.password == "p1"


def test_cli_config_fail_closed_without_provider_secret():
    provider = MemorySecretProvider()
    with pytest.raises(ValueError) as exc:
        CliConfigInput(
            username="user1",
            password=None,
            setor_emissor="IEE3",
            setor_executor="IEE3",
            report_kind="pendentes",
            base_url="https://osprd.itaipu/SAM_SMA/",
            headless=True,
            download_dir="downloads",
            staging_dir="staging",
            secure_required=True,
            allow_transitional_plaintext=False,
            secret_service="svc",
            secret_provider=provider,
        ).to_scrape_config()
    assert "secret set" in str(exc.value)


def test_cli_config_invalid_selector_mode():
    provider = MemorySecretProvider()
    provider.set_secret("svc", "user1", "p1")
    with pytest.raises(ValueError):
        CliConfigInput(
            username="user1",
            password=None,
            setor_emissor="IEE3",
            setor_executor="IEE3",
            report_kind="pendentes",
            base_url="https://osprd.itaipu/SAM_SMA/",
            headless=True,
            download_dir="downloads",
            staging_dir="staging",
            secure_required=False,
            allow_transitional_plaintext=True,
            secret_service="svc",
            secret_provider=provider,
            selector_mode="invalid",
        ).to_scrape_config()


def test_cli_config_ignore_https_errors_flag():
    provider = MemorySecretProvider()
    provider.set_secret("svc", "user1", "p1")
    cfg = CliConfigInput(
        username="user1",
        password=None,
        setor_emissor="IEE3",
        setor_executor="IEE3",
        report_kind="pendentes",
        base_url="https://osprd.itaipu/SAM_SMA/",
        headless=True,
        download_dir="downloads",
        staging_dir="staging",
        secure_required=True,
        allow_transitional_plaintext=False,
        secret_service="svc",
        secret_provider=provider,
        ignore_https_errors=True,
    ).to_scrape_config()
    assert cfg.ignore_https_errors is True


def test_build_recent_emission_year_week_window_uses_current_week_and_4_weeks_back():
    start_value, end_value = build_recent_emission_year_week_window(date(2026, 3, 16))
    assert start_value == "202608"
    assert end_value == "202612"


def test_build_recent_emission_year_week_window_handles_year_boundary():
    start_value, end_value = build_recent_emission_year_week_window(date(2026, 1, 5))
    assert start_value == "202550"
    assert end_value == "202602"


def test_cli_config_derives_emission_year_week_window():
    provider = MemorySecretProvider()
    provider.set_secret("svc", "user1", "p1")
    cfg = CliConfigInput(
        username="user1",
        password=None,
        setor_emissor="IEE3",
        setor_executor="IEE3",
        report_kind="pendentes",
        base_url="https://osprd.itaipu/SAM_SMA/",
        headless=True,
        download_dir="downloads",
        staging_dir="staging",
        secure_required=True,
        allow_transitional_plaintext=False,
        secret_service="svc",
        secret_provider=provider,
    ).to_scrape_config()
    assert cfg.emission_year_week_start
    assert cfg.emission_year_week_end
    assert len(cfg.emission_year_week_start) == 6
    assert len(cfg.emission_year_week_end) == 6


def test_normalize_emission_date_accepts_iso_and_br_formats():
    assert normalize_emission_date("25/12/2025") == "25/12/2025"
    assert normalize_emission_date("2025-12-25") == "25/12/2025"
    assert normalize_emission_date("25122025") == "25/12/2025"


def test_normalize_emission_date_rejects_mmddyyyy():
    with pytest.raises(ValueError, match="MM/DD/YYYY nao e suportado"):
        normalize_emission_date("12/31/2025")


def test_cli_config_accepts_emission_date_window():
    provider = MemorySecretProvider()
    provider.set_secret("svc", "user1", "p1")
    cfg = CliConfigInput(
        username="user1",
        password=None,
        setor_emissor="OUO5",
        setor_executor="ALL",
        report_kind="pendentes",
        base_url="https://osprd.itaipu/SAM_SMA/",
        headless=True,
        download_dir="downloads",
        staging_dir="staging",
        secure_required=True,
        allow_transitional_plaintext=False,
        secret_service="svc",
        secret_provider=provider,
        emission_date_start="2025-12-25",
        emission_date_end="2025-12-25",
    ).to_scrape_config()
    assert cfg.emission_date_start == "25/12/2025"
    assert cfg.emission_date_end == "25/12/2025"
    assert cfg.emission_year_week_start == ""
    assert cfg.emission_year_week_end == ""


def test_cli_config_rejects_mixed_emission_date_and_year_week():
    with pytest.raises(ValueError, match="nao misturar filtro por ano/semana com data de emissao"):
        ScrapeConfig(
            username="user1",
            password="p1",
            setor_emissor="IEE3",
            setor_executor="MEL4",
            report_kind="pendentes",
            download_dir=Path("downloads"),
            staging_dir=Path("staging"),
            emission_year_week_start="202551",
            emission_year_week_end="202552",
            emission_date_start="25/12/2025",
            emission_date_end="25/12/2025",
        )


def test_scrape_config_rejects_partial_or_inverted_emission_date(tmp_path):
    with pytest.raises(ValueError, match="filtro por data de emissao exige inicio e fim"):
        CliConfigInput(
            username="user1",
            password="p1",
            setor_emissor="IEE3",
            setor_executor="MEL4",
            report_kind="pendentes",
            base_url="https://osprd.itaipu/SAM_SMA/",
            headless=True,
            download_dir=str(tmp_path / "downloads1"),
            staging_dir=str(tmp_path / "staging1"),
            secure_required=False,
            allow_transitional_plaintext=True,
            secret_service="svc",
            secret_provider=None,
            emission_date_start="25/12/2025",
            emission_date_end=None,
        ).to_scrape_config()

    with pytest.raises(ValueError, match="data de emissao inicial nao pode ser maior que a final"):
        CliConfigInput(
            username="user1",
            password="p1",
            setor_emissor="IEE3",
            setor_executor="MEL4",
            report_kind="pendentes",
            base_url="https://osprd.itaipu/SAM_SMA/",
            headless=True,
            download_dir=str(tmp_path / "downloads2"),
            staging_dir=str(tmp_path / "staging2"),
            secure_required=False,
            allow_transitional_plaintext=True,
            secret_service="svc",
            secret_provider=None,
            emission_date_start="26/12/2025",
            emission_date_end="25/12/2025",
        ).to_scrape_config()


def test_cli_config_keeps_setor_emissor():
    provider = MemorySecretProvider()
    provider.set_secret("svc", "user1", "p1")
    cfg = CliConfigInput(
        username="user1",
        password=None,
        setor_emissor="IEE3",
        setor_executor="MEL4",
        report_kind="pendentes",
        base_url="https://osprd.itaipu/SAM_SMA/",
        headless=True,
        download_dir="downloads",
        staging_dir="staging",
        secure_required=True,
        allow_transitional_plaintext=False,
        secret_service="svc",
        secret_provider=provider,
    ).to_scrape_config()
    assert cfg.setor_emissor == "IEE3"
    assert cfg.setor_executor == "MEL4"


def test_cli_config_keeps_numero_ssa():
    provider = MemorySecretProvider()
    provider.set_secret("svc", "user1", "p1")
    cfg = CliConfigInput(
        username="user1",
        password=None,
        setor_emissor="ALL",
        setor_executor="ALL",
        numero_ssa=" 202603879 ",
        report_kind="consulta_ssa",
        base_url="https://osprd.itaipu/SAM_SMA/",
        headless=True,
        download_dir="downloads",
        staging_dir="staging",
        secure_required=True,
        allow_transitional_plaintext=False,
        secret_service="svc",
        secret_provider=provider,
    ).to_scrape_config()
    assert cfg.numero_ssa == "202603879"


def test_cli_config_accepts_pendentes_execucao():
    provider = MemorySecretProvider()
    provider.set_secret("svc", "user1", "p1")
    cfg = CliConfigInput(
        username="user1",
        password=None,
        setor_emissor="IEE3",
        setor_executor="MEL4",
        report_kind="pendentes_execucao",
        base_url="https://osprd.itaipu/SAM_SMA/",
        headless=True,
        download_dir="downloads",
        staging_dir="staging",
        secure_required=True,
        allow_transitional_plaintext=False,
        secret_service="svc",
        secret_provider=provider,
    ).to_scrape_config()
    assert cfg.report_kind == "pendentes_execucao"


def test_cli_config_accepts_consulta_ssa():
    provider = MemorySecretProvider()
    provider.set_secret("svc", "user1", "p1")
    cfg = CliConfigInput(
        username="user1",
        password=None,
        setor_emissor="IEE3",
        setor_executor="MEL4",
        report_kind="consulta_ssa",
        base_url="https://osprd.itaipu/SAM_SMA/",
        headless=True,
        download_dir="downloads",
        staging_dir="staging",
        secure_required=True,
        allow_transitional_plaintext=False,
        secret_service="svc",
        secret_provider=provider,
    ).to_scrape_config()
    assert cfg.report_kind == "consulta_ssa"


def test_cli_config_accepts_consulta_ssa_print():
    provider = MemorySecretProvider()
    provider.set_secret("svc", "user1", "p1")
    cfg = CliConfigInput(
        username="user1",
        password=None,
        setor_emissor="IEE3",
        setor_executor="MEL4",
        report_kind="consulta_ssa_print",
        base_url="https://osprd.itaipu/SAM_SMA/",
        headless=True,
        download_dir="downloads",
        staging_dir="staging",
        secure_required=True,
        allow_transitional_plaintext=False,
        secret_service="svc",
        secret_provider=provider,
    ).to_scrape_config()
    assert cfg.report_kind == "consulta_ssa_print"


def test_cli_config_accepts_reprogramacoes():
    provider = MemorySecretProvider()
    provider.set_secret("svc", "user1", "p1")
    cfg = CliConfigInput(
        username="user1",
        password=None,
        setor_emissor="IEE3",
        setor_executor="MEL4",
        report_kind="reprogramacoes",
        base_url="https://osprd.itaipu/SAM_SMA/",
        headless=True,
        download_dir="downloads",
        staging_dir="staging",
        secure_required=True,
        allow_transitional_plaintext=False,
        secret_service="svc",
        secret_provider=provider,
    ).to_scrape_config()
    assert cfg.report_kind == "reprogramacoes"


def test_cli_config_accepts_aprovacao_emissao():
    provider = MemorySecretProvider()
    provider.set_secret("svc", "user1", "p1")
    cfg = CliConfigInput(
        username="user1",
        password=None,
        setor_emissor="IEE3",
        setor_executor="MEL4",
        report_kind="aprovacao_emissao",
        base_url="https://osprd.itaipu/SAM_SMA/",
        headless=True,
        download_dir="downloads",
        staging_dir="staging",
        secure_required=True,
        allow_transitional_plaintext=False,
        secret_service="svc",
        secret_provider=provider,
    ).to_scrape_config()
    assert cfg.report_kind == "aprovacao_emissao"


def test_cli_config_accepts_aprovacao_cancelamento():
    provider = MemorySecretProvider()
    provider.set_secret("svc", "user1", "p1")
    cfg = CliConfigInput(
        username="user1",
        password=None,
        setor_emissor="IEE3",
        setor_executor="MEL4",
        report_kind="aprovacao_cancelamento",
        base_url="https://osprd.itaipu/SAM_SMA/",
        headless=True,
        download_dir="downloads",
        staging_dir="staging",
        secure_required=True,
        allow_transitional_plaintext=False,
        secret_service="svc",
        secret_provider=provider,
    ).to_scrape_config()
    assert cfg.report_kind == "aprovacao_cancelamento"


def test_cli_config_accepts_derivadas_relacionadas():
    provider = MemorySecretProvider()
    provider.set_secret("svc", "user1", "p1")
    cfg = CliConfigInput(
        username="user1",
        password=None,
        setor_emissor="IEE3",
        setor_executor="MEL4",
        report_kind="derivadas_relacionadas",
        base_url="https://osprd.itaipu/SAM_SMA/",
        headless=True,
        download_dir="downloads",
        staging_dir="staging",
        secure_required=True,
        allow_transitional_plaintext=False,
        secret_service="svc",
        secret_provider=provider,
    ).to_scrape_config()
    assert cfg.report_kind == "derivadas_relacionadas"
