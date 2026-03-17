import pytest

from datetime import date

from scrap_report.config import CliConfigInput, build_recent_emission_year_week_window
from scrap_report.secret_provider import MemorySecretProvider


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
