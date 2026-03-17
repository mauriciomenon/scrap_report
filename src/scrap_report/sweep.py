"""Base de planejamento para varredura multipla de setores e filtros."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .config import SETOR_PRIORITY_GROUPS, normalize_setor_filter

SWEEP_SCOPE_MODES = ("emissor", "executor", "ambos", "nenhum")
SETOR_GROUP_ALIASES = {
    "principal": "principal",
    "segundo_plano": "segundo_plano",
    "terceiro_plano": "terceiro_plano",
    "demais": "demais",
    "prioritarios": ("principal", "segundo_plano", "terceiro_plano"),
}


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


@dataclass(frozen=True, slots=True)
class FilterSpec:
    scope_mode: str
    setor_emissor: str | None = None
    setor_executor: str | None = None
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
                        emission_year_week_start=self.emission_year_week_start,
                        emission_year_week_end=self.emission_year_week_end,
                        emission_date_start=self.emission_date_start,
                        emission_date_end=self.emission_date_end,
                    )
                )
        return tuple(specs)
