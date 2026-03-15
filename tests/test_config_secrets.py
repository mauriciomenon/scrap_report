import pytest

from scrap_report.config import CliConfigInput
from scrap_report.secret_provider import MemorySecretProvider


def test_cli_config_uses_provider_secret():
    provider = MemorySecretProvider()
    provider.set_secret("svc", "user1", "p1")
    cfg = CliConfigInput(
        username="user1",
        password=None,
        setor_executor="IEE3",
        report_kind="pendentes",
        base_url="https://apps.itaipu.gov.br/SAM/",
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
            setor_executor="IEE3",
            report_kind="pendentes",
            base_url="https://apps.itaipu.gov.br/SAM/",
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
            setor_executor="IEE3",
            report_kind="pendentes",
            base_url="https://apps.itaipu.gov.br/SAM/",
            headless=True,
            download_dir="downloads",
            staging_dir="staging",
            secure_required=False,
            allow_transitional_plaintext=True,
            secret_service="svc",
            secret_provider=provider,
            selector_mode="invalid",
        ).to_scrape_config()
