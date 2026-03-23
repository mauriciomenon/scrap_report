"""Base de planejamento e execucao de varredura multipla."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .config import (
    EMISSION_DATE_SUPPORTED_REPORT_KINDS,
    ScrapeConfig,
    SETOR_PRIORITY_GROUPS,
    build_recent_emission_year_week_window,
    normalize_setor_filter,
)
from .pipeline import run_pipeline

SWEEP_SCOPE_MODES = ("emissor", "executor", "ambos", "nenhum")
SWEEP_PRESET_SCOPES = ("emissor", "executor", "ambos")
SETOR_GROUP_ALIASES = {
    "principal": "principal",
    "segundo_plano": "segundo_plano",
    "terceiro_plano": "terceiro_plano",
    "demais": "demais",
    "prioritarios": ("principal", "segundo_plano", "terceiro_plano"),
}
SWEEP_PRESET_NAMES = tuple(
    f"{group_name}_{scope_name}"
    for group_name in ("principal", "segundo_plano", "terceiro_plano", "prioritarios", "demais")
    for scope_name in SWEEP_PRESET_SCOPES
)


def _dedupe_keep_order(values: Iterable[str]) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return tuple(ordered)


def _normalize_group_token(value: str) -> str:
    return value.strip().lower()


def _resolve_group_alias(group_name: str) -> tuple[str, ...]:
    normalized_group = _normalize_group_token(group_name)
    alias = SETOR_GROUP_ALIASES.get(normalized_group)
    if isinstance(alias, tuple):
        return alias
    if isinstance(alias, str):
        return (alias,)
    raise ValueError("preset de grupo invalido")


def expand_setor_targets(targets: Sequence[str]) -> tuple[str, ...]:
    expanded: list[str] = []
    for target in targets:
        normalized_group = _normalize_group_token(target)
        alias = SETOR_GROUP_ALIASES.get(normalized_group)
        if isinstance(alias, tuple):
            for group_name in alias:
                expanded.extend(SETOR_PRIORITY_GROUPS[group_name])
            continue
        if isinstance(alias, str):
            expanded.extend(SETOR_PRIORITY_GROUPS[alias])
            continue

        normalized_setor = normalize_setor_filter(target)
        if normalized_setor is None:
            raise ValueError(
                "token de sweep nao pode ser ALL/vazio; use scope_mode='nenhum' para sem filtro"
            )
        expanded.append(normalized_setor)
    return _dedupe_keep_order(expanded)


def build_preset_plan(preset_name: str, report_kind: str) -> "SweepPlan":
    normalized = preset_name.strip().lower()
    if normalized not in SWEEP_PRESET_NAMES:
        raise ValueError("preset invalido")

    group_name, scope_mode = normalized.rsplit("_", 1)
    if scope_mode not in SWEEP_PRESET_SCOPES:
        raise ValueError("preset invalido")

    year_week_start, year_week_end = build_recent_emission_year_week_window()
    if scope_mode == "emissor":
        return SweepPlan(
            report_kind=report_kind,
            scope_mode="emissor",
            setores_emissor=(group_name,),
            emission_year_week_start=year_week_start,
            emission_year_week_end=year_week_end,
        )
    if scope_mode == "executor":
        return SweepPlan(
            report_kind=report_kind,
            scope_mode="executor",
            setores_executor=(group_name,),
            emission_year_week_start=year_week_start,
            emission_year_week_end=year_week_end,
        )
    return SweepPlan(
        report_kind=report_kind,
        scope_mode="ambos",
        setores_emissor=(group_name,),
        setores_executor=(group_name,),
        emission_year_week_start=year_week_start,
        emission_year_week_end=year_week_end,
    )


@dataclass(frozen=True, slots=True)
class FilterSpec:
    scope_mode: str
    setor_emissor: str | None = None
    setor_executor: str | None = None
    numero_ssa: str | None = None
    emission_year_week_start: str | None = None
    emission_year_week_end: str | None = None
    emission_date_start: str | None = None
    emission_date_end: str | None = None

    def __post_init__(self) -> None:
        normalized_scope = self.scope_mode.strip().lower()
        if normalized_scope not in SWEEP_SCOPE_MODES:
            raise ValueError("scope_mode invalido")
        object.__setattr__(self, "scope_mode", normalized_scope)
        object.__setattr__(self, "setor_emissor", normalize_setor_filter(self.setor_emissor))
        object.__setattr__(self, "setor_executor", normalize_setor_filter(self.setor_executor))
        object.__setattr__(self, "numero_ssa", (self.numero_ssa or "").strip() or None)

        self._validate_scope()
        self._validate_time_filter()

    def _validate_scope(self) -> None:
        if self.scope_mode == "emissor":
            if not self.setor_emissor or self.setor_executor:
                raise ValueError("scope_mode emissor exige apenas setor_emissor")
            return
        if self.scope_mode == "executor":
            if not self.setor_executor or self.setor_emissor:
                raise ValueError("scope_mode executor exige apenas setor_executor")
            return
        if self.scope_mode == "ambos":
            if not self.setor_emissor or not self.setor_executor:
                raise ValueError("scope_mode ambos exige setor_emissor e setor_executor")
            return
        if self.setor_emissor or self.setor_executor:
            raise ValueError("scope_mode nenhum nao aceita setores")

    def _validate_time_filter(self) -> None:
        has_year_week = bool(self.emission_year_week_start or self.emission_year_week_end)
        has_date = bool(self.emission_date_start or self.emission_date_end)
        if has_year_week and has_date:
            raise ValueError("nao misturar filtro por ano/semana com data de emissao")
        if bool(self.emission_year_week_start) != bool(self.emission_year_week_end):
            raise ValueError("filtro por ano/semana exige inicio e fim")
        if bool(self.emission_date_start) != bool(self.emission_date_end):
            raise ValueError("filtro por data de emissao exige inicio e fim")


@dataclass(frozen=True, slots=True)
class SweepPlan:
    report_kind: str
    scope_mode: str
    setores_emissor: tuple[str, ...] = ()
    setores_executor: tuple[str, ...] = ()
    numero_ssa: str | None = None
    emission_year_week_start: str | None = None
    emission_year_week_end: str | None = None
    emission_date_start: str | None = None
    emission_date_end: str | None = None

    def __post_init__(self) -> None:
        normalized_scope = self.scope_mode.strip().lower()
        if normalized_scope not in SWEEP_SCOPE_MODES:
            raise ValueError("scope_mode invalido")
        object.__setattr__(self, "scope_mode", normalized_scope)
        object.__setattr__(self, "setores_emissor", expand_setor_targets(self.setores_emissor))
        object.__setattr__(self, "setores_executor", expand_setor_targets(self.setores_executor))
        object.__setattr__(self, "numero_ssa", (self.numero_ssa or "").strip() or None)
        self._validate_scope_inputs()
        self._validate_time_filter()

    def _validate_scope_inputs(self) -> None:
        if self.scope_mode == "emissor":
            if not self.setores_emissor or self.setores_executor:
                raise ValueError("sweep emissor exige lista apenas de setores_emissor")
            return
        if self.scope_mode == "executor":
            if not self.setores_executor or self.setores_emissor:
                raise ValueError("sweep executor exige lista apenas de setores_executor")
            return
        if self.scope_mode == "ambos":
            if not self.setores_emissor or not self.setores_executor:
                raise ValueError("sweep ambos exige listas de emissor e executor")
            return
        if self.setores_emissor or self.setores_executor:
            raise ValueError("sweep nenhum nao aceita listas de setores")

    def _validate_time_filter(self) -> None:
        has_year_week = bool(self.emission_year_week_start or self.emission_year_week_end)
        has_date = bool(self.emission_date_start or self.emission_date_end)
        if has_year_week and has_date:
            raise ValueError("nao misturar filtro por ano/semana com data de emissao")
        if bool(self.emission_year_week_start) != bool(self.emission_year_week_end):
            raise ValueError("filtro por ano/semana exige inicio e fim")
        if bool(self.emission_date_start) != bool(self.emission_date_end):
            raise ValueError("filtro por data de emissao exige inicio e fim")

    def expand(self) -> tuple[FilterSpec, ...]:
        if self.scope_mode == "nenhum":
            return (
                FilterSpec(
                    scope_mode="nenhum",
                    numero_ssa=self.numero_ssa,
                    emission_year_week_start=self.emission_year_week_start,
                    emission_year_week_end=self.emission_year_week_end,
                    emission_date_start=self.emission_date_start,
                    emission_date_end=self.emission_date_end,
                ),
            )
        if self.scope_mode == "emissor":
            return tuple(
                FilterSpec(
                    scope_mode="emissor",
                    setor_emissor=setor,
                    numero_ssa=self.numero_ssa,
                    emission_year_week_start=self.emission_year_week_start,
                    emission_year_week_end=self.emission_year_week_end,
                    emission_date_start=self.emission_date_start,
                    emission_date_end=self.emission_date_end,
                )
                for setor in self.setores_emissor
            )
        if self.scope_mode == "executor":
            return tuple(
                FilterSpec(
                    scope_mode="executor",
                    setor_executor=setor,
                    numero_ssa=self.numero_ssa,
                    emission_year_week_start=self.emission_year_week_start,
                    emission_year_week_end=self.emission_year_week_end,
                    emission_date_start=self.emission_date_start,
                    emission_date_end=self.emission_date_end,
                )
                for setor in self.setores_executor
            )
        specs: list[FilterSpec] = []
        for setor_emissor in self.setores_emissor:
            for setor_executor in self.setores_executor:
                specs.append(
                    FilterSpec(
                        scope_mode="ambos",
                        setor_emissor=setor_emissor,
                        setor_executor=setor_executor,
                        numero_ssa=self.numero_ssa,
                        emission_year_week_start=self.emission_year_week_start,
                        emission_year_week_end=self.emission_year_week_end,
                        emission_date_start=self.emission_date_start,
                        emission_date_end=self.emission_date_end,
                    )
                )
        return tuple(specs)

    def expand_items(self) -> tuple["SweepItem", ...]:
        return tuple(
            SweepItem(index=index, filter_spec=filter_spec)
            for index, filter_spec in enumerate(self.expand(), start=1)
        )


@dataclass(frozen=True, slots=True)
class SweepItem:
    index: int
    filter_spec: FilterSpec


@dataclass(frozen=True, slots=True)
class SweepRuntimeConfig:
    username: str
    password: str
    base_url: str = "https://osprd.itaipu/SAM_SMA/"
    headless: bool = True
    download_dir: Path = Path("downloads")
    staging_dir: Path = Path("staging")
    selector_mode: str = "adaptive"
    ignore_https_errors: bool = False
    generate_reports: bool = True


@dataclass(frozen=True, slots=True)
class SweepItemResult:
    index: int
    scope_mode: str
    setor_emissor: str | None
    setor_executor: str | None
    numero_ssa: str | None
    emission_year_week_start: str | None
    emission_year_week_end: str | None
    emission_date_start: str | None
    emission_date_end: str | None
    status: str
    source_path: Path | None = None
    staged_path: Path | None = None
    reports: dict[str, str] | None = None
    telemetry: dict[str, int] | None = None
    error: str | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "index": self.index,
            "scope_mode": self.scope_mode,
            "setor_emissor": self.setor_emissor,
            "setor_executor": self.setor_executor,
            "numero_ssa": self.numero_ssa,
            "emission_year_week_start": self.emission_year_week_start,
            "emission_year_week_end": self.emission_year_week_end,
            "emission_date_start": self.emission_date_start,
            "emission_date_end": self.emission_date_end,
            "status": self.status,
            "source_path": str(self.source_path) if self.source_path else None,
            "staged_path": str(self.staged_path) if self.staged_path else None,
            "reports": self.reports or {},
            "telemetry": self.telemetry or {},
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class SweepManifest:
    status: str
    report_kind: str
    scope_mode: str
    item_count: int
    success_count: int
    failure_count: int
    items: tuple[SweepItemResult, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "report_kind": self.report_kind,
            "scope_mode": self.scope_mode,
            "item_count": self.item_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "items": [item.to_payload() for item in self.items],
        }


class SweepRunner:
    def __init__(self, pipeline_runner=run_pipeline) -> None:
        self._pipeline_runner = pipeline_runner

    def run(self, plan: SweepPlan, runtime: SweepRuntimeConfig) -> SweepManifest:
        results = tuple(
            self._run_item(item=item, report_kind=plan.report_kind, runtime=runtime)
            for item in plan.expand_items()
        )
        success_count = sum(1 for item in results if item.status == "ok")
        failure_count = len(results) - success_count
        if failure_count == 0:
            status = "ok"
        elif success_count == 0:
            status = "error"
        else:
            status = "partial"
        return SweepManifest(
            status=status,
            report_kind=plan.report_kind,
            scope_mode=plan.scope_mode,
            item_count=len(results),
            success_count=success_count,
            failure_count=failure_count,
            items=results,
        )

    def _run_item(
        self,
        item: SweepItem,
        report_kind: str,
        runtime: SweepRuntimeConfig,
    ) -> SweepItemResult:
        spec = item.filter_spec
        if (spec.emission_date_start or spec.emission_date_end) and (
            report_kind not in EMISSION_DATE_SUPPORTED_REPORT_KINDS
        ):
            error = f"report_kind={report_kind} nao suporta filtro por data de emissao validado"
            if report_kind == "aprovacao_emissao":
                error += "; export atual nao entrega Emitida Em confiavel"
            else:
                error += " neste runtime"
            return SweepItemResult(
                index=item.index,
                scope_mode=spec.scope_mode,
                setor_emissor=spec.setor_emissor,
                setor_executor=spec.setor_executor,
                numero_ssa=spec.numero_ssa,
                emission_year_week_start=spec.emission_year_week_start,
                emission_year_week_end=spec.emission_year_week_end,
                emission_date_start=spec.emission_date_start,
                emission_date_end=spec.emission_date_end,
                status="error",
                error=error,
            )
        config = ScrapeConfig(
            username=runtime.username,
            password=runtime.password,
            setor_emissor=spec.setor_emissor,
            setor_executor=spec.setor_executor,
            numero_ssa=spec.numero_ssa or "",
            report_kind=report_kind,
            base_url=runtime.base_url,
            headless=runtime.headless,
            download_dir=runtime.download_dir,
            staging_dir=runtime.staging_dir,
            selector_mode=runtime.selector_mode,
            ignore_https_errors=runtime.ignore_https_errors,
            emission_year_week_start=spec.emission_year_week_start or "",
            emission_year_week_end=spec.emission_year_week_end or "",
            emission_date_start=spec.emission_date_start or "",
            emission_date_end=spec.emission_date_end or "",
        )
        try:
            pipeline_result = self._pipeline_runner(
                config,
                generate_reports=runtime.generate_reports,
            )
        except Exception as exc:
            return SweepItemResult(
                index=item.index,
                scope_mode=spec.scope_mode,
                setor_emissor=spec.setor_emissor,
                setor_executor=spec.setor_executor,
                numero_ssa=spec.numero_ssa,
                emission_year_week_start=spec.emission_year_week_start,
                emission_year_week_end=spec.emission_year_week_end,
                emission_date_start=spec.emission_date_start,
                emission_date_end=spec.emission_date_end,
                status="error",
                error=str(exc),
            )

        return SweepItemResult(
            index=item.index,
            scope_mode=spec.scope_mode,
            setor_emissor=spec.setor_emissor,
            setor_executor=spec.setor_executor,
            numero_ssa=spec.numero_ssa,
            emission_year_week_start=spec.emission_year_week_start,
            emission_year_week_end=spec.emission_year_week_end,
            emission_date_start=spec.emission_date_start,
            emission_date_end=spec.emission_date_end,
            status=pipeline_result.status,
            source_path=pipeline_result.source_path,
            staged_path=pipeline_result.staged_path,
            reports=dict(pipeline_result.reports),
            telemetry=dict(pipeline_result.telemetry),
        )
