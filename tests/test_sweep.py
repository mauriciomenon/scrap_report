from pathlib import Path
from typing import Any, cast

import pytest

from scrap_report.config import REST_SWEEP_SUPPORTED_REPORT_KINDS
from scrap_report.reporting import SAMApiArtifacts
from scrap_report.sweep import (
    FilterSpec,
    SweepPlan,
    SweepRunner,
    SweepRuntimeConfig,
    SWEEP_PRESET_NAMES,
    _infer_rest_number_of_years,
    build_preset_plan,
    expand_setor_targets,
)


def _manifest_payload(manifest: Any) -> dict[str, Any]:
    return cast(dict[str, Any], manifest.to_payload())


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


def test_infer_rest_number_of_years_accepts_iso_emission_date():
    spec = FilterSpec(
        scope_mode="nenhum",
        emission_date_start="2026-02-23",
        emission_date_end="2026-02-25",
    )

    assert _infer_rest_number_of_years(spec) == 1


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
    assert manifest.runtime_mode == "playwright"
    payload = _manifest_payload(manifest)
    assert [item["setor_executor"] for item in payload["items"]] == ["MEL4", "MEL3"]


def test_sweep_runner_available_artifacts_skip_missing_paths(tmp_path: Path):
    plan = SweepPlan(
        report_kind="pendentes",
        scope_mode="executor",
        setores_executor=("MEL4",),
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
        staged_path = runtime.staging_dir / "ok.xlsx"
        report_path = runtime.staging_dir / "reports" / "dados.xlsx"
        missing_path = runtime.download_dir / "old.xlsx"
        staged_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        staged_path.write_bytes(b"xlsx")
        report_path.write_bytes(b"report")

        result = cast(Any, type("PipelineResult", (), {})())
        result.status = "ok"
        result.source_path = missing_path
        result.staged_path = staged_path
        result.reports = {
            "dados": str(report_path),
            "old": str(missing_path),
            "mode": "search",
        }
        result.telemetry = None
        return result

    manifest = SweepRunner(pipeline_runner=_pipeline_runner).run(plan, runtime)

    payload = _manifest_payload(manifest)
    item = payload["items"][0]
    available = cast(dict[str, Any], item["available_artifacts"])
    assert item["telemetry"] == {}
    assert "source_path" not in available
    assert available["staged_path"] == str(runtime.staging_dir / "ok.xlsx")
    assert available["reports"] == {
        "dados": str(runtime.staging_dir / "reports" / "dados.xlsx")
    }


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
    payload = _manifest_payload(manifest)
    assert payload["items"][0]["numero_ssa"] == "202603879"


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
    payload = _manifest_payload(manifest)
    assert payload["items"][1]["status"] == "error"
    assert payload["items"][1]["error"] == "falha de teste"


def test_sweep_runner_passes_emission_date_to_pipeline(tmp_path: Path):
    plan = SweepPlan(
        report_kind="consulta_ssa",
        scope_mode="nenhum",
        numero_ssa="202602521",
        emission_date_start="2026-02-23",
        emission_date_end="2026-02-23",
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
    assert seen["emission_date_start"] == "23/02/2026"
    assert seen["emission_date_end"] == "23/02/2026"
    assert seen["emission_year_week_start"] == ""
    assert seen["emission_year_week_end"] == ""


def test_sweep_runner_rejects_unsupported_emission_date_report_kind(tmp_path: Path):
    plan = SweepPlan(
        report_kind="aprovacao_emissao",
        scope_mode="nenhum",
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
    assert (
        "nao suporta filtro por data de emissao validado; export atual nao entrega Emitida Em confiavel"
        in (manifest.items[0].error or "")
    )


def test_sweep_runner_rest_mode_exports_records_for_pendentes(tmp_path: Path):
    plan = SweepPlan(
        report_kind="pendentes",
        scope_mode="emissor",
        setores_emissor=("IEE3",),
        emission_year_week_start="202608",
        emission_year_week_end="202612",
    )
    runtime = SweepRuntimeConfig(
        username="u1",
        password="p1",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
        runtime_mode="rest",
        rest_base_url="https://example/rest",
        rest_timeout_seconds=45.0,
        rest_verify_tls=False,
        rest_ca_file=str(tmp_path / "corp-ca.pem"),
    )
    seen = {}

    class _FakeClient:
        def __init__(self, base_url, timeout_seconds, verify_tls, ca_file=None):
            seen["base_url"] = base_url
            seen["timeout_seconds"] = timeout_seconds
            seen["verify_tls"] = verify_tls
            seen["ca_file"] = ca_file

    def _fake_query_runner(**kwargs):
        seen["query_kwargs"] = kwargs
        return (
            "search",
            [
                {
                    "ssa_number": "202600001",
                    "executor_sector": "MEL4",
                    "emitter_sector": "IEE3",
                    "detail_present": False,
                    "year_week": 202609,
                }
            ],
        )

    def _fake_exporter(records, output_dir, prefix):
        seen["records"] = records
        seen["output_dir"] = output_dir
        seen["prefix"] = prefix
        output_dir.mkdir(parents=True, exist_ok=True)
        data_csv = output_dir / f"{prefix}.csv"
        data_xlsx = output_dir / f"{prefix}.xlsx"
        summary_xlsx = output_dir / f"{prefix}_summary.xlsx"
        data_csv.write_text("ssa_number\n202600001\n", encoding="utf-8")
        data_xlsx.write_text("xlsx", encoding="utf-8")
        summary_xlsx.write_text("summary", encoding="utf-8")
        return SAMApiArtifacts(
            data_csv=data_csv,
            data_xlsx=data_xlsx,
            summary_xlsx=summary_xlsx,
        )

    manifest = SweepRunner(
        sam_api_client_factory=_FakeClient,
        sam_api_query_runner=_fake_query_runner,
        sam_api_artifacts_exporter=_fake_exporter,
    ).run(plan, runtime)

    payload = _manifest_payload(manifest)
    assert manifest.status == "ok"
    assert manifest.runtime_mode == "rest"
    assert payload["runtime_mode"] == "rest"
    assert payload["items"][0]["runtime_mode"] == "rest"
    assert seen["base_url"] == "https://example/rest"
    assert seen["timeout_seconds"] == 45.0
    assert seen["verify_tls"] is False
    assert seen["ca_file"] == str(tmp_path / "corp-ca.pem")
    assert seen["query_kwargs"]["emitter_sectors"] == ("IEE3",)
    assert seen["query_kwargs"]["number_of_years"] == 1
    assert seen["query_kwargs"]["include_details"] is True
    assert seen["prefix"] == "pendentes_001"
    assert "rest_sweep" in str(seen["output_dir"])
    assert payload["items"][0]["reports"]["mode"] == "search"
    assert payload["items"][0]["telemetry"]["record_count"] == 1
    assert payload["items"][0]["telemetry"]["without_detail_count"] == 1


def test_sweep_runner_rest_mode_rejects_unsupported_report_kind(tmp_path: Path):
    plan = SweepPlan(
        report_kind="executadas",
        scope_mode="nenhum",
        emission_year_week_start="202608",
        emission_year_week_end="202612",
    )
    runtime = SweepRuntimeConfig(
        username="u1",
        password="p1",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
        runtime_mode="rest",
    )

    manifest = SweepRunner().run(plan, runtime)

    assert manifest.status == "error"
    assert manifest.runtime_mode == "rest"
    assert manifest.items[0].runtime_mode == "rest"
    assert (
        "suporta apenas report_kind=" + ",".join(REST_SWEEP_SUPPORTED_REPORT_KINDS)
    ) in (manifest.items[0].error or "")
    assert "GetSSABySSANumber" not in (manifest.items[0].error or "")


def test_sweep_runner_rest_mode_supports_multiple_items(tmp_path: Path):
    plan = SweepPlan(
        report_kind="pendentes",
        scope_mode="emissor",
        setores_emissor=("IEE3", "IEE1"),
        emission_year_week_start="202608",
        emission_year_week_end="202612",
    )
    runtime = SweepRuntimeConfig(
        username="u1",
        password="p1",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
        runtime_mode="rest",
    )
    seen_emitters: list[tuple[str, ...]] = []

    class _FakeClient:
        def __init__(self, base_url, timeout_seconds, verify_tls, ca_file=None):
            pass

    def _fake_query_runner(**kwargs):
        emitter_sectors = tuple(kwargs["emitter_sectors"])
        seen_emitters.append(emitter_sectors)
        emitter = emitter_sectors[0]
        return (
            "search",
            [
                {
                    "ssa_number": f"{emitter}-1",
                    "executor_sector": "MEL4",
                    "emitter_sector": emitter,
                    "detail_present": False,
                    "year_week": 202609,
                }
            ],
        )

    def _fake_exporter(records, output_dir, prefix):
        output_dir.mkdir(parents=True, exist_ok=True)
        data_csv = output_dir / f"{prefix}.csv"
        data_xlsx = output_dir / f"{prefix}.xlsx"
        summary_xlsx = output_dir / f"{prefix}_summary.xlsx"
        data_csv.write_text("ssa_number\n", encoding="utf-8")
        data_xlsx.write_text("xlsx", encoding="utf-8")
        summary_xlsx.write_text("summary", encoding="utf-8")
        return SAMApiArtifacts(data_csv=data_csv, data_xlsx=data_xlsx, summary_xlsx=summary_xlsx)

    manifest = SweepRunner(
        sam_api_client_factory=_FakeClient,
        sam_api_query_runner=_fake_query_runner,
        sam_api_artifacts_exporter=_fake_exporter,
    ).run(plan, runtime)

    assert manifest.status == "ok"
    assert manifest.item_count == 2
    assert manifest.success_count == 2
    assert seen_emitters == [("IEE3",), ("IEE1",)]


def test_sweep_runner_rest_mode_supports_unfiltered_scope(tmp_path: Path):
    plan = SweepPlan(
        report_kind="pendentes",
        scope_mode="nenhum",
        emission_year_week_start="202608",
        emission_year_week_end="202612",
    )
    runtime = SweepRuntimeConfig(
        username="u1",
        password="p1",
        download_dir=tmp_path / "downloads",
        staging_dir=tmp_path / "staging",
        runtime_mode="rest",
    )
    seen = {}

    class _FakeClient:
        def __init__(self, base_url, timeout_seconds, verify_tls, ca_file=None):
            pass

    def _fake_query_runner(**kwargs):
        seen["executor_sectors"] = kwargs["executor_sectors"]
        seen["emitter_sectors"] = kwargs["emitter_sectors"]
        seen["number_of_years"] = kwargs["number_of_years"]
        return (
            "search",
            [
                {
                    "ssa_number": "202600001",
                    "executor_sector": "MEL4",
                    "emitter_sector": "IEE3",
                    "detail_present": False,
                    "year_week": 202609,
                }
            ],
        )

    def _fake_exporter(records, output_dir, prefix):
        output_dir.mkdir(parents=True, exist_ok=True)
        data_csv = output_dir / f"{prefix}.csv"
        data_xlsx = output_dir / f"{prefix}.xlsx"
        summary_xlsx = output_dir / f"{prefix}_summary.xlsx"
        data_csv.write_text("ssa_number\n202600001\n", encoding="utf-8")
        data_xlsx.write_text("xlsx", encoding="utf-8")
        summary_xlsx.write_text("summary", encoding="utf-8")
        return SAMApiArtifacts(data_csv=data_csv, data_xlsx=data_xlsx, summary_xlsx=summary_xlsx)

    manifest = SweepRunner(
        sam_api_client_factory=_FakeClient,
        sam_api_query_runner=_fake_query_runner,
        sam_api_artifacts_exporter=_fake_exporter,
    ).run(plan, runtime)

    assert manifest.status == "ok"
    assert manifest.item_count == 1
    assert seen["executor_sectors"] == ()
    assert seen["emitter_sectors"] == ()
    assert seen["number_of_years"] == 1


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
    assert plan.emission_year_week_start is not None
    assert plan.emission_year_week_end is not None
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
