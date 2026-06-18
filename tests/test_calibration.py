from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from glutenix.calibration.literature import (
    compare_pasta_cooking_records,
    load_literature_records,
    pasta_calibration_report_markdown,
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
        assert len(records) == 9
        assert records[0].measured["cooking_loss_pct"] > 0
        assert abs(sum(records[0].mapped_formula.values()) - 1.0) < 1e-6

    def test_compare_pasta_cooking_records(self):
        session = _seeded_session()
        try:
            result = compare_pasta_cooking_records(session)
        finally:
            session.close()

        assert result["n_records"] == 9
        assert result["metric"] == "cooking_loss_pct"
        assert result["before"]["rmse"] >= 0
        assert result["after"]["rmse"] >= 0
        assert len(result["rows"]) == 9
        assert "alpha" in result["correction"]

    def test_report_markdown(self):
        session = _seeded_session()
        try:
            result = compare_pasta_cooking_records(session)
        finally:
            session.close()

        report = pasta_calibration_report_markdown(result)
        assert "# Pasta Cooking Literature Calibration Report" in report
        assert "Before correction" in report
