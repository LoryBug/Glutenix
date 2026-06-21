import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from glutenix.calibration.literature import (
    DEFAULT_BREAD_DATASET,
    compare_bread_baking_records,
    compare_pasta_cooking_records,
    load_literature_records,
    pasta_calibration_report_markdown,
    validate_literature_dataset,
)
from glutenix.calibration.coverage import (
    assess_application_literature_coverage,
    summarize_literature_coverage,
)
from glutenix.db.base import Base
from glutenix.db.seed import _seed_applications, _seed_ingredients


def _seeded_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    _seed_ingredients(session)
    _seed_applications(session)
    session.commit()
    return session


class TestLiteratureCalibration:
    def test_load_literature_records(self):
        records = load_literature_records()
        assert len(records) == 40
        assert records[0].measured["cooking_loss_pct"] > 0
        assert "water_absorption_pct" in records[0].measured
        assert abs(sum(records[0].mapped_formula.values()) - 1.0) < 1e-6

    def test_validate_literature_dataset_summary(self):
        summary = validate_literature_dataset()

        assert summary["record_count"] == 40
        assert summary["applications"] == ["Pasta fresca"]
        assert summary["source_count"] == 3
        assert "cooking_loss_pct" in summary["metrics"]
        assert "swelling_index" in summary["metrics"]

    def test_validate_bread_literature_dataset_summary(self):
        records = load_literature_records(
            DEFAULT_BREAD_DATASET,
            required_measured_metrics=(),
            required_process_fields=("hydration_pct", "baking_time_min"),
        )
        summary = validate_literature_dataset(
            DEFAULT_BREAD_DATASET,
            required_measured_metrics=(),
            required_process_fields=("hydration_pct", "baking_time_min"),
        )

        assert summary["record_count"] == len(records)
        assert summary["applications"] == ["Pane"]
        assert summary["source_count"] == len({record.source.get("doi") for record in records})
        assert "specific_volume_cm3_g" in summary["metrics"]
        assert "crumb_hardness_n" in summary["metrics"]
        assert "porosity_pct" in summary["metrics"]

        belorio_records = [record for record in records if record.id.startswith("belorio_2020_")]
        assert len(belorio_records) == 6
        assert all("specific_volume_cm3_g" in record.measured for record in belorio_records)
        assert all("crumb_hardness_n" in record.measured for record in belorio_records)

        wojcik_records = [record for record in records if record.id.startswith("wojcik_2021_")]
        assert len(wojcik_records) == 6
        assert all("specific_volume_cm3_g" in record.measured for record in wojcik_records)
        assert all("crumb_hardness_n" in record.measured for record in wojcik_records)

        di_renzo_records = [record for record in records if record.id.startswith("di_renzo_2024_")]
        assert len(di_renzo_records) == 5
        assert all(record.source.get("doi") == "10.3390/foods13091382" for record in di_renzo_records)
        assert all("specific_volume_cm3_g" in record.measured for record in di_renzo_records)
        assert any("Kappa carrageenan" in record.mapped_formula for record in di_renzo_records)

    def test_compare_pasta_cooking_records(self):
        session = _seeded_session()
        try:
            result = compare_pasta_cooking_records(session)
        finally:
            session.close()

        assert result["n_records"] == 40
        assert result["source_count"] == 3
        assert result["metric"] == "cooking_loss_pct"
        assert result["before"]["rmse"] >= 0
        assert result["after"]["rmse"] >= 0
        assert result["before"]["mae"] < 2.0
        assert "water_absorption_pct" in result["metric_summaries"]
        assert "swelling_index" in result["metric_summaries"]
        assert "source" in result["grouped_errors"]
        assert "process_family" in result["grouped_errors"]
        assert "flour_water_ratio" in result["grouped_errors"]
        assert result["record_groups"]["process_family"] == {
            "dried_extruded": 10,
            "fresh_calcium_gel": 30,
        }
        assert result["record_groups"]["source"] == {
            "10.1002/fsn3.3301": 30,
            "10.1007/s13197-016-2323-8": 5,
            "10.1016/j.fochx.2025.103403": 5,
        }
        assert len(result["rows"]) == 40
        assert "alpha" in result["correction"]
        assert result["rows"][0]["water_to_flour_ratio"] == 2.0
        assert result["rows"][0]["process_family"] == "fresh_calcium_gel"
        assert result["rows"][0]["gelation_index"] > 0
        assert result["rows"][0]["pregelatinization_index"] > 0

    def test_compare_bread_baking_records(self):
        records = load_literature_records(
            DEFAULT_BREAD_DATASET,
            required_measured_metrics=(),
            required_process_fields=("hydration_pct", "baking_time_min"),
        )
        session = _seeded_session()
        try:
            result = compare_bread_baking_records(session)
        finally:
            session.close()

        assert result["n_records"] == len(records)
        assert result["source_count"] == len({record.source.get("doi") for record in records})
        assert result["metric"] == "specific_volume_cm3_g"
        assert "specific_volume_cm3_g" in result["metric_summaries"]
        assert "crumb_hardness_n" in result["metric_summaries"]
        assert "porosity_pct" in result["metric_summaries"]
        assert result["record_groups"]["process_family"] == {
            "commercial_mix_bread": 4,
            "enzyme_bread": 1,
            "enzyme_hydrocolloid_bread": 12,
            "generic_gluten_free_bread": 2,
            "hydrocolloid_bread": 21,
            "millet_cultivar_bread": 9,
            "protein_enriched_bread": 16,
        }
        assert len(result["rows"]) == len(records)
        assert result["rows"][0]["simulated_specific_volume_cm3_g"] > 0

    def test_literature_coverage_summary(self):
        session = _seeded_session()
        try:
            result = summarize_literature_coverage(session)
        finally:
            session.close()

        assert set(result["domains"]) == {"pasta_cooking", "bread_baking"}
        bread = result["domains"]["bread_baking"]
        records = load_literature_records(
            DEFAULT_BREAD_DATASET,
            required_measured_metrics=(),
            required_process_fields=("hydration_pct", "baking_time_min"),
        )
        assert bread["record_count"] == len(records)
        assert bread["source_count"] == len({record.source.get("doi") for record in records})
        assert "hydration_pct" in bread["process_ranges"]
        assert "tg_pct" in bread["process_ranges"]
        assert "hydrocolloid_bread" in bread["process_families"]
        assert "enzyme_hydrocolloid_bread" in bread["process_families"]
        assert "HPMC (Hydroxypropyl Methylcellulose)" in bread["covered_ingredients"]
        assert "Kappa carrageenan" in bread["covered_ingredients"]
        assert "Potato starch" in bread["covered_ingredients"]

    def test_literature_coverage_assessment_flags_ood(self):
        session = _seeded_session()
        try:
            assessment = assess_application_literature_coverage(
                application="Pane",
                ingredient_names=["White rice flour", "Sorghum flour"],
                blend_values={
                    "protein_pct": 5.0,
                    "starch_pct": 90.0,
                    "fat_pct": 0.5,
                    "fiber_pct": 1.0,
                    "water_absorption": 4.5,
                    "viscosity_index": 0.5,
                    "hydrocolloid_pct": 0.0,
                    "amylose_pct": 22.0,
                },
                process_values={
                    "hydration_pct": 65.0,
                    "baking_temp_c": 280.0,
                    "baking_time_min": 15.0,
                },
                db=session,
            )
        finally:
            session.close()

        assert assessment.level in {"low", "medium"}
        assert assessment.risk_flags
        assert any("Sorghum flour" in flag for flag in assessment.risk_flags)
        assert any("baking_temp_c" in flag for flag in assessment.risk_flags)
        assert any("baking_time_min" in flag for flag in assessment.risk_flags)

    def test_literature_coverage_assessment_flags_tg_mechanism_ood(self):
        session = _seeded_session()
        try:
            assessment = assess_application_literature_coverage(
                application="Pane",
                ingredient_names=["Quinoa flour", "HPMC (Hydroxypropyl Methylcellulose)"],
                blend_values={
                    "protein_pct": 14.0,
                    "starch_pct": 58.0,
                    "fat_pct": 6.0,
                    "fiber_pct": 6.0,
                    "water_absorption": 1.8,
                    "viscosity_index": 2.0,
                    "hydrocolloid_pct": 0.01,
                    "amylose_pct": 11.0,
                },
                process_values={
                    "hydration_pct": 90.0,
                    "baking_temp_c": 170.0,
                    "baking_time_min": 25.0,
                    "tg_pct": 0.75,
                },
                db=session,
            )
        finally:
            session.close()

        assert assessment.level == "low"
        assert assessment.mechanism_coverage == 0.0
        assert assessment.calibration_coverage < 0.5
        assert any("tg_pct" in flag for flag in assessment.risk_flags)

    def test_literature_coverage_assessment_downgrades_sparse_quinoa(self):
        session = _seeded_session()
        try:
            assessment = assess_application_literature_coverage(
                application="Pane",
                ingredient_names=["Quinoa flour", "White rice flour"],
                blend_values={
                    "protein_pct": 9.0,
                    "starch_pct": 74.0,
                    "fat_pct": 1.0,
                    "fiber_pct": 2.0,
                    "water_absorption": 1.6,
                    "viscosity_index": 1.4,
                    "hydrocolloid_pct": 0.0,
                    "amylose_pct": 18.0,
                },
                process_values={
                    "hydration_pct": 100.0,
                    "baking_temp_c": 190.0,
                    "baking_time_min": 35.0,
                },
                db=session,
            )
        finally:
            session.close()

        assert assessment.level == "low"
        assert assessment.calibration_coverage < 0.5
        assert any("Quinoa flour" in flag for flag in assessment.risk_flags)

    def test_literature_coverage_plain_hydrocolloid_keeps_medium_or_high(self):
        session = _seeded_session()
        try:
            assessment = assess_application_literature_coverage(
                application="Pane",
                ingredient_names=["White rice flour", "Corn starch", "HPMC (Hydroxypropyl Methylcellulose)"],
                blend_values={
                    "protein_pct": 7.0,
                    "starch_pct": 78.0,
                    "fat_pct": 1.0,
                    "fiber_pct": 2.0,
                    "water_absorption": 1.8,
                    "viscosity_index": 2.0,
                    "hydrocolloid_pct": 0.02,
                    "amylose_pct": 22.0,
                },
                process_values={
                    "hydration_pct": 100.0,
                    "baking_temp_c": 190.0,
                    "baking_time_min": 35.0,
                    "tg_pct": 0.0,
                },
                db=session,
            )
        finally:
            session.close()

        assert assessment.level in {"medium", "high"}
        assert assessment.mechanism_coverage == 1.0
        assert assessment.calibration_coverage >= 0.75

    def test_report_markdown(self):
        session = _seeded_session()
        try:
            result = compare_pasta_cooking_records(session)
        finally:
            session.close()

        report = pasta_calibration_report_markdown(result)
        assert "# Pasta Cooking Literature Calibration Report" in report
        assert "Before correction" in report
        assert "process_family" in report

    def test_invalid_literature_dataset_fails(self, tmp_path):
        dataset = tmp_path / "invalid.jsonl"
        dataset.write_text(
            '{"id":"bad","application":"Pasta fresca","source":{"title":"x","doi":"10.x"},'
            '"literature_formula":{"amaranth_flour":1.0},'
            '"mapped_formula":{"Amaranth flour":0.5},"mapping_notes":"x",'
            '"process":{"cooking_time_min":5},"measured":{"cooking_loss_pct":1},'
            '"confidence":"high"}\n',
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="mapped_formula must sum to 1.0"):
            validate_literature_dataset(dataset)
