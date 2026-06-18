import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from glutenix.calibration.literature import (
    compare_pasta_cooking_records,
    load_literature_records,
    pasta_calibration_report_markdown,
    validate_literature_dataset,
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
