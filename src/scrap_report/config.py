"""Configuracao central para pipeline de scraping e staging."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .secret_provider import SecretBackendUnavailableError, SecretNotFoundError, SecretProvider

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SECRET_SETUP_HINT = (
    "configure secret seguro com: "
    "uv run python -m scrap_report.cli secret set "
    "--username <usuario> --password <valor> --secret-service scrap_report.sam"
)


def _resolve_project_path(value: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


@dataclass(slots=True)
class ScrapeConfig:
    """Configuracao de execucao do pipeline."""

    username: str
    password: str
    setor_executor: str
    report_kind: str = "pendentes"
    base_url: str = "https://apps.itaipu.gov.br/SAM/"
    headless: bool = True
    download_dir: Path = PROJECT_ROOT / "downloads"
    staging_dir: Path = PROJECT_ROOT / "staging"
    navigation_timeout_ms: int = 20000
    loading_timeout_ms: int = 60000
    download_timeout_ms: int = 90000
    selector_timeout_ms: int = 10000
    network_idle_timeout_ms: int = 5000
    retry_attempts: int = 3
    selector_mode: str = "adaptive"

    def __post_init__(self) -> None:
        self.report_kind = self.report_kind.strip().lower()
        if self.report_kind not in {"pendentes", "executadas"}:
            raise ValueError("report_kind deve ser 'pendentes' ou 'executadas'")
        self.selector_mode = self.selector_mode.strip().lower()
        if self.selector_mode not in {"strict", "adaptive"}:
            raise ValueError("selector_mode deve ser 'strict' ou 'adaptive'")

        if not self.username.strip():
            raise ValueError("username nao pode ser vazio")
        if not self.password.strip():
            raise ValueError("password nao pode ser vazio")
        if not self.setor_executor.strip():
            raise ValueError("setor_executor nao pode ser vazio")

        self.download_dir = _resolve_project_path(Path(self.download_dir))
        self.staging_dir = _resolve_project_path(Path(self.staging_dir))
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.staging_dir.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class CliConfigInput:
    """Entradas opcionais da CLI para criar ScrapeConfig."""

    username: str | None
    password: str | None
    setor_executor: str
    report_kind: str
    base_url: str
    headless: bool
    download_dir: str
    staging_dir: str
    secure_required: bool = False
    allow_transitional_plaintext: bool = True
    secret_service: str = "scrap_report.sam"
    secret_provider: SecretProvider | None = None
    selector_mode: str = "adaptive"

    def to_scrape_config(self) -> ScrapeConfig:
        username = (self.username or os.getenv("SAM_USERNAME", "")).strip()
        password = self._resolve_password(username)

        return ScrapeConfig(
            username=username,
            password=password,
            setor_executor=self.setor_executor,
            report_kind=self.report_kind,
            base_url=self.base_url,
            headless=self.headless,
            download_dir=Path(self.download_dir),
            staging_dir=Path(self.staging_dir),
            selector_mode=self.selector_mode,
        )

    def _resolve_password(self, username: str) -> str:
        if not username:
            return ""
        if self.password:
            return self.password.strip()

        provider = self.secret_provider
        if provider is not None:
            try:
                return provider.get_secret(self.secret_service, username).strip()
            except (SecretNotFoundError, SecretBackendUnavailableError):
                if self.secure_required or not self.allow_transitional_plaintext:
                    raise ValueError(
                        "execucao bloqueada: secret seguro indisponivel para usuario informado. "
                        + SECRET_SETUP_HINT
                    ) from None

        env_password = os.getenv("SAM_PASSWORD", "").strip()
        if env_password and self.allow_transitional_plaintext:
            return env_password

        if self.secure_required or not self.allow_transitional_plaintext:
            raise ValueError(
                "execucao bloqueada: secret seguro obrigatorio. " + SECRET_SETUP_HINT
            )
        return ""
