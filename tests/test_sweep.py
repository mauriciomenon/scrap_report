import pytest

from scrap_report.sweep import FilterSpec, SweepPlan, expand_setor_targets


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
