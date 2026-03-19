from pathlib import Path

import pytest

from scrap_report.sweep import (
    FilterSpec,
    SweepPlan,
    SweepRunner,
    SweepRuntimeConfig,
    SWEEP_PRESET_NAMES,
    build_preset_plan,
    expand_setor_targets,
)


def test_expand_setor_targets_keeps_priority_order_and_dedupes():
    expanded = expand_setor_targets(("principal", "MEL4", "MEL3", "IEE1"))

    assert expanded == ("IEE3", "MEL4", "MEL3", "IEE1")


def test_expand_setor_targets_supports_prioritarios_alias():
    expanded = expand_setor_targets(("prioritarios",))

    assert expanded == (
        "IEE3",
        "MEL4",
        "MEL3",
        "IEE1",
        "IEE2",
        "IEE4",
        "MEL1",
        "MEL2",
        "IEQ1",
        "IEQ2",
        "IEQ3",
        "ILA1",
        "ILA2",
        "ILA3",
    )


def test_expand_setor_targets_rejects_all_token():
    with pytest.raises(ValueError):
        expand_setor_targets(("ALL",))


def test_filter_spec_rejects_mixed_time_modes():
    with pytest.raises(ValueError):
        FilterSpec(
            scope_mode="emissor",
            setor_emissor="IEE3",
            emission_year_week_start="202608",
            emission_year_week_end="202612",
            emission_date_start="2026-03-01",
            emission_date_end="2026-03-17",
        )


def test_sweep_plan_emissor_expands_group():
    plan = SweepPlan(
        report_kind="pendentes",
        scope_mode="emissor",
        setores_emissor=("principal",),
        emission_year_week_start="202608",
        emission_year_week_end="202612",
    )

    specs = plan.expand()

    assert [spec.setor_emissor for spec in specs] == ["IEE3", "MEL4", "MEL3"]
    assert all(spec.scope_mode == "emissor" for spec in specs)
    assert all(spec.setor_executor is None for spec in specs)


def test_sweep_plan_executor_expands_direct_values():
    plan = SweepPlan(
        report_kind="pendentes",
        scope_mode="executor",
        setores_executor=("MEL4", "MEL3"),
        emission_year_week_start="202608",
        emission_year_week_end="202612",
    )

    specs = plan.expand()

    assert [spec.setor_executor for spec in specs] == ["MEL4", "MEL3"]
    assert all(spec.scope_mode == "executor" for spec in specs)
    assert all(spec.setor_emissor is None for spec in specs)


def test_sweep_plan_ambos_builds_cartesian_product_in_order():
    plan = SweepPlan(
        report_kind="pendentes",
        scope_mode="ambos",
        setores_emissor=("IEE3", "IEE1"),
        setores_executor=("MEL4", "MEL3"),
        emission_year_week_start="202608",
        emission_year_week_end="202612",
    )

    specs = plan.expand()

    assert [
        (spec.setor_emissor, spec.setor_executor) for spec in specs
    ] == [
        ("IEE3", "MEL4"),
        ("IEE3", "MEL3"),
        ("IEE1", "MEL4"),
        ("IEE1", "MEL3"),
    ]


def test_sweep_plan_nenhum_returns_single_unfiltered_spec():
    plan = SweepPlan(
        report_kind="pendentes",
        scope_mode="nenhum",
        emission_year_week_start="202608",
        emission_year_week_end="202612",
    )

    specs = plan.expand()

    assert len(specs) == 1
    assert specs[0].setor_emissor is None
    assert specs[0].setor_executor is None


def test_sweep_runner_keeps_order_and_collects_successes(tmp_path: Path):
    plan = SweepPlan(
        report_kind="pendentes",
        scope_mode="executor",
        setores_executor=("MEL4", "MEL3"),
        emission_year_week_start="202608",
        emission_year_week_end="202612",
    )
    runtime = SweepRuntimeConfig(
        username="u1",
        password="p1",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
    )
    seen: list[str | None] = []

    def _pipeline_runner(config, generate_reports):
        seen.append(config.setor_executor)
        return type(
            "PipelineResult",
            (),
            {
                "status": "ok",
                "source_path": runtime.download_dir / f"{config.setor_executor}.xlsx",
                "staged_path": runtime.staging_dir / f"{config.setor_executor}.xlsx",
                "reports": {"dados": f"{config.setor_executor}.xlsx"},
                "telemetry": {"pipeline_ms": 1},
            },
        )()

    manifest = SweepRunner(pipeline_runner=_pipeline_runner).run(plan, runtime)

    assert seen == ["MEL4", "MEL3"]
    assert manifest.status == "ok"
    assert manifest.success_count == 2
    assert manifest.failure_count == 0
    assert [item["setor_executor"] for item in manifest.to_payload()["items"]] == ["MEL4", "MEL3"]


def test_sweep_runner_passes_numero_ssa_to_pipeline(tmp_path: Path):
    plan = SweepPlan(
        report_kind="consulta_ssa",
        scope_mode="nenhum",
        numero_ssa="202603879",
        emission_year_week_start="202608",
        emission_year_week_end="202612",
    )
    runtime = SweepRuntimeConfig(
        username="u1",
        password="p1",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
    )
    seen = {}

    def _pipeline_runner(config, generate_reports):
        seen["numero_ssa"] = config.numero_ssa
        return type(
            "PipelineResult",
            (),
            {
                "status": "ok",
                "source_path": runtime.download_dir / "ok.xlsx",
                "staged_path": runtime.staging_dir / "ok.xlsx",
                "reports": {"dados": "ok.xlsx"},
                "telemetry": {"pipeline_ms": 1},
            },
        )()

    manifest = SweepRunner(pipeline_runner=_pipeline_runner).run(plan, runtime)

    assert manifest.status == "ok"
    assert seen["numero_ssa"] == "202603879"
    assert manifest.to_payload()["items"][0]["numero_ssa"] == "202603879"


def test_sweep_runner_continues_after_failure(tmp_path: Path):
    plan = SweepPlan(
        report_kind="pendentes",
        scope_mode="ambos",
        setores_emissor=("IEE3",),
        setores_executor=("MEL4", "MEL3"),
        emission_year_week_start="202608",
        emission_year_week_end="202612",
    )
    runtime = SweepRuntimeConfig(
        username="u1",
        password="p1",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
    )

    def _pipeline_runner(config, generate_reports):
        if config.setor_executor == "MEL3":
            raise RuntimeError("falha de teste")
        return type(
            "PipelineResult",
            (),
            {
                "status": "ok",
                "source_path": runtime.download_dir / "ok.xlsx",
                "staged_path": runtime.staging_dir / "ok.xlsx",
                "reports": {"dados": "ok.xlsx"},
                "telemetry": {"pipeline_ms": 1},
            },
        )()

    manifest = SweepRunner(pipeline_runner=_pipeline_runner).run(plan, runtime)

    assert manifest.status == "partial"
    assert manifest.success_count == 1
    assert manifest.failure_count == 1
    payload = manifest.to_payload()
    assert payload["items"][1]["status"] == "error"
    assert payload["items"][1]["error"] == "falha de teste"


def test_sweep_runner_passes_emission_date_to_pipeline(tmp_path: Path):
    plan = SweepPlan(
        report_kind="pendentes",
        scope_mode="executor",
        setores_executor=("MEL4",),
        emission_date_start="2025-12-25",
        emission_date_end="2025-12-25",
    )
    runtime = SweepRuntimeConfig(
        username="u1",
        password="p1",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
    )
    seen = {}

    def _pipeline_runner(config, generate_reports):
        seen["emission_date_start"] = config.emission_date_start
        seen["emission_date_end"] = config.emission_date_end
        seen["emission_year_week_start"] = config.emission_year_week_start
        seen["emission_year_week_end"] = config.emission_year_week_end
        return type(
            "PipelineResult",
            (),
            {
                "status": "ok",
                "source_path": runtime.download_dir / "ok.xlsx",
                "staged_path": runtime.staging_dir / "ok.xlsx",
                "reports": {"dados": "ok.xlsx"},
                "telemetry": {"pipeline_ms": 1},
            },
        )()

    manifest = SweepRunner(pipeline_runner=_pipeline_runner).run(plan, runtime)

    assert manifest.status == "ok"
    assert manifest.failure_count == 0
    assert seen["emission_date_start"] == "25/12/2025"
    assert seen["emission_date_end"] == "25/12/2025"
    assert seen["emission_year_week_start"] == ""
    assert seen["emission_year_week_end"] == ""


def test_sweep_runner_rejects_unsupported_emission_date_report_kind(tmp_path: Path):
    plan = SweepPlan(
        report_kind="consulta_ssa",
        scope_mode="executor",
        setores_executor=("MEL4",),
        emission_date_start="2025-12-25",
        emission_date_end="2025-12-25",
    )
    runtime = SweepRuntimeConfig(
        username="u1",
        password="p1",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
    )

    manifest = SweepRunner().run(plan, runtime)

    assert manifest.status == "error"
    assert manifest.failure_count == 1
    assert "nao suporta filtro por data de emissao validado" in (manifest.items[0].error or "")


def test_preset_names_include_priority_groups_and_scope_modes():
    assert "principal_executor" in SWEEP_PRESET_NAMES
    assert "principal_emissor" in SWEEP_PRESET_NAMES
    assert "principal_ambos" in SWEEP_PRESET_NAMES
    assert "prioritarios_executor" in SWEEP_PRESET_NAMES


def test_build_preset_plan_executor_uses_recent_weeks():
    plan = build_preset_plan("principal_executor", "pendentes")

    assert plan.scope_mode == "executor"
    assert plan.setores_executor == ("IEE3", "MEL4", "MEL3")
    assert plan.setores_emissor == ()
    assert len(plan.emission_year_week_start) == 6
    assert len(plan.emission_year_week_end) == 6


def test_build_preset_plan_emissor_uses_group_only_on_emissor():
    plan = build_preset_plan("segundo_plano_emissor", "pendentes")

    assert plan.scope_mode == "emissor"
    assert plan.setores_emissor == ("IEE1", "IEE2", "IEE4")
    assert plan.setores_executor == ()


def test_build_preset_plan_ambos_uses_same_group_on_both_sides():
    plan = build_preset_plan("terceiro_plano_ambos", "pendentes")

    assert plan.scope_mode == "ambos"
    assert plan.setores_emissor == ("MEL1", "MEL2", "IEQ1", "IEQ2", "IEQ3", "ILA1", "ILA2", "ILA3")
    assert plan.setores_executor == ("MEL1", "MEL2", "IEQ1", "IEQ2", "IEQ3", "ILA1", "ILA2", "ILA3")
