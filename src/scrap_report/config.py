"""Configuracao central para pipeline de scraping e staging."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from .secret_provider import SecretBackendUnavailableError, SecretNotFoundError, SecretProvider

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SETOR_EMISSOR = "IEE3"
DEFAULT_SETOR_EXECUTOR = "MEL4"
SETOR_ALL_TOKENS = ("", "*", "ALL", "TODOS", "TODAS")
SETOR_PRIORITY_GROUPS = {
    "principal": ("IEE3", "MEL4", "MEL3"),
    "segundo_plano": ("IEE1", "IEE2", "IEE4"),
    "terceiro_plano": ("MEL1", "MEL2", "IEQ1", "IEQ2", "IEQ3", "ILA1", "ILA2", "ILA3"),
    "demais": (),
}
REPORT_KINDS = (
    "pendentes",
    "executadas",
    "pendentes_execucao",
    "consulta_ssa",
    "consulta_ssa_print",
    "aprovacao_emissao",
    "aprovacao_cancelamento",
    "derivadas_relacionadas",
    "reprogramacoes",
)
VALIDATED_FILTER_CAPABILITIES = {
    "pendentes": frozenset(
        {"setor_emissor", "setor_executor", "emission_year_week", "emission_date"}
    ),
    "executadas": frozenset(
        {"setor_emissor", "setor_executor", "emission_year_week", "emission_date"}
    ),
    "pendentes_execucao": frozenset({"setor_emissor", "setor_executor", "emission_year_week"}),
    "consulta_ssa": frozenset(
        {"numero_ssa", "setor_emissor", "setor_executor", "emission_year_week"}
    ),
    "consulta_ssa_print": frozenset(
        {"numero_ssa", "setor_emissor", "setor_executor", "emission_year_week"}
    ),
    "aprovacao_emissao": frozenset({"setor_emissor", "setor_executor", "emission_year_week"}),
    "aprovacao_cancelamento": frozenset(
        {"setor_emissor", "setor_executor", "emission_year_week"}
    ),
    "derivadas_relacionadas": frozenset({"setor_emissor", "setor_executor", "emission_year_week"}),
    "reprogramacoes": frozenset({"setor_emissor", "setor_executor", "emission_year_week"}),
}
EMISSION_DATE_SUPPORTED_REPORT_KINDS = tuple(
    kind
    for kind, filters in VALIDATED_FILTER_CAPABILITIES.items()
    if "emission_date" in filters
)
NON_REPORT_GENERATION_KINDS = ("consulta_ssa_print",)
NON_XLSX_DOWNLOAD_KINDS = ("consulta_ssa_print",)
SECRET_SETUP_HINT = (
    "configure secret seguro com: "
    "uv run python -m scrap_report.cli secret setup "
    "--username <usuario> --secret-service scrap_report.sam"
)


def _resolve_project_path(value: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def normalize_setor_filter(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    if normalized in SETOR_ALL_TOKENS:
        return None
    return normalized


def build_recent_emission_year_week_window(
    reference_date: date | None = None, weeks_back: int = 4
) -> tuple[str, str]:
    target_date = reference_date or date.today()
    start_date = target_date - timedelta(weeks=weeks_back)
    start_iso = start_date.isocalendar()
    end_iso = target_date.isocalendar()
    start_value = f"{start_iso.year}{start_iso.week:02d}"
    end_value = f"{end_iso.year}{end_iso.week:02d}"
    return start_value, end_value


def normalize_emission_date(value: str | None) -> str:
    if value is None:
        return ""
    normalized = value.strip()
    if not normalized:
        return ""
    if re.fullmatch(r"\d{8}", normalized):
        try:
            parsed = datetime.strptime(normalized, "%d%m%Y")
            return parsed.strftime("%d/%m/%Y")
        except ValueError:
            raise ValueError(
                "data de emissao deve estar em DD/MM/YYYY, DDMMYYYY ou YYYY-MM-DD"
            ) from None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(normalized, fmt)
            return parsed.strftime("%d/%m/%Y")
        except ValueError:
            continue
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", normalized):
        try:
            datetime.strptime(normalized, "%m/%d/%Y")
        except ValueError:
            pass
        else:
            raise ValueError(
                "formato MM/DD/YYYY nao e suportado; use DD/MM/YYYY, DDMMYYYY ou YYYY-MM-DD"
            )
    raise ValueError("data de emissao deve estar em DD/MM/YYYY, DDMMYYYY ou YYYY-MM-DD")


def normalize_text_filter(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip()


def report_kind_supports_filter(report_kind: str, filter_name: str) -> bool:
    return filter_name in VALIDATED_FILTER_CAPABILITIES.get(report_kind, frozenset())


def report_kind_uses_excel_output(report_kind: str) -> bool:
    return report_kind not in NON_REPORT_GENERATION_KINDS


def report_kind_download_suffixes(report_kind: str) -> tuple[str, ...]:
    if report_kind in NON_XLSX_DOWNLOAD_KINDS:
        return (".pdf",)
    return (".xlsx",)


@dataclass(slots=True)
class ScrapeConfig:
    """Configuracao de execucao do pipeline."""

    username: str
    password: str
    setor_executor: str | None = DEFAULT_SETOR_EXECUTOR
    setor_emissor: str | None = DEFAULT_SETOR_EMISSOR
    report_kind: str = "pendentes"
    base_url: str = "https://osprd.itaipu/SAM_SMA/"
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
    ignore_https_errors: bool = False
    numero_ssa: str = ""
    emission_year_week_start: str = ""
    emission_year_week_end: str = ""
    emission_date_start: str = ""
    emission_date_end: str = ""

    def __post_init__(self) -> None:
        self.report_kind = self.report_kind.strip().lower()
        if self.report_kind not in REPORT_KINDS:
            raise ValueError(
                "report_kind deve ser 'pendentes', 'executadas', 'pendentes_execucao', "
                "'consulta_ssa', 'consulta_ssa_print', 'aprovacao_emissao', "
                "'aprovacao_cancelamento', 'derivadas_relacionadas' ou 'reprogramacoes'"
            )
        self.selector_mode = self.selector_mode.strip().lower()
        if self.selector_mode not in {"strict", "adaptive"}:
            raise ValueError("selector_mode deve ser 'strict' ou 'adaptive'")

        if not self.username.strip():
            raise ValueError("username nao pode ser vazio")
        if not self.password.strip():
            raise ValueError("password nao pode ser vazio")
        self.numero_ssa = normalize_text_filter(self.numero_ssa)
        self.setor_emissor = normalize_setor_filter(self.setor_emissor)
        self.setor_executor = normalize_setor_filter(self.setor_executor)
        self.emission_date_start = normalize_emission_date(self.emission_date_start)
        self.emission_date_end = normalize_emission_date(self.emission_date_end)

        has_year_week = bool(self.emission_year_week_start or self.emission_year_week_end)
        has_date = bool(self.emission_date_start or self.emission_date_end)
        if has_year_week and has_date:
            raise ValueError("nao misturar filtro por ano/semana com data de emissao")
        if bool(self.emission_year_week_start) != bool(self.emission_year_week_end):
            raise ValueError("filtro por ano/semana exige inicio e fim")
        if bool(self.emission_date_start) != bool(self.emission_date_end):
            raise ValueError("filtro por data de emissao exige inicio e fim")
        if has_date:
            start_date = datetime.strptime(self.emission_date_start, "%d/%m/%Y").date()
            end_date = datetime.strptime(self.emission_date_end, "%d/%m/%Y").date()
            if start_date > end_date:
                raise ValueError("data de emissao inicial nao pode ser maior que a final")
        elif not has_year_week:
            (
                self.emission_year_week_start,
                self.emission_year_week_end,
            ) = build_recent_emission_year_week_window()

        self.download_dir = _resolve_project_path(Path(self.download_dir))
        self.staging_dir = _resolve_project_path(Path(self.staging_dir))
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.staging_dir.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class CliConfigInput:
    """Entradas opcionais da CLI para criar ScrapeConfig."""

    username: str | None
    password: str | None
    setor_executor: str | None
    report_kind: str
    base_url: str
    headless: bool
    download_dir: str
    staging_dir: str
    setor_emissor: str | None = DEFAULT_SETOR_EMISSOR
    secure_required: bool = False
    allow_transitional_plaintext: bool = True
    secret_service: str = "scrap_report.sam"
    secret_provider: SecretProvider | None = None
    selector_mode: str = "adaptive"
    ignore_https_errors: bool = False
    numero_ssa: str | None = None
    emission_date_start: str | None = None
    emission_date_end: str | None = None

    def to_scrape_config(self) -> ScrapeConfig:
        username = (self.username or os.getenv("SAM_USERNAME", "")).strip()
        password = self._resolve_password(username)

        return ScrapeConfig(
            username=username,
            password=password,
            setor_emissor=self.setor_emissor,
            setor_executor=self.setor_executor,
            report_kind=self.report_kind,
            base_url=self.base_url,
            headless=self.headless,
            download_dir=Path(self.download_dir),
            staging_dir=Path(self.staging_dir),
            selector_mode=self.selector_mode,
            ignore_https_errors=self.ignore_https_errors,
            numero_ssa=self.numero_ssa or "",
            emission_date_start=self.emission_date_start or "",
            emission_date_end=self.emission_date_end or "",
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
