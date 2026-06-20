"""Tests for the ML residual benchmark module."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from glutenix.db.base import Base
from glutenix.db.seed import _seed_applications, _seed_ingredients
from glutenix.ml.residual import (
    BenchmarkMetrics,
    BREAD_PROCESS_FEATURES,
    build_bread_dataset,
    build_pasta_dataset,
    benchmark_bread,
    benchmark_pasta,
)


def _seeded_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    _seed_ingredients(session)
    _seed_applications(session)
    session.commit()
    return session


class TestResidualDataset:
    def test_build_bread_dataset(self):
        session = _seeded_session()
        try:
            ds = build_bread_dataset(session)
            assert ds["n_records"] == 60
            assert "specific_volume_cm3_g" in ds["dataset"]
            assert "crumb_hardness_n" in ds["dataset"]
            assert "porosity_pct" in ds["dataset"]
            vol_data = ds["dataset"]["specific_volume_cm3_g"]
            assert vol_data["X"].shape[0] == 54
            assert vol_data["y_true"].shape[0] == 54
            assert vol_data["y_sim"].shape[0] == 54
            assert len(vol_data["sources"]) == 54
            assert "tg_pct" in BREAD_PROCESS_FEATURES
        finally:
            session.close()

    def test_build_pasta_dataset(self):
        session = _seeded_session()
        try:
            ds = build_pasta_dataset(session)
            assert ds["n_records"] == 40
            assert "cooking_loss_pct" in ds["dataset"]
            loss_data = ds["dataset"]["cooking_loss_pct"]
            assert loss_data["X"].shape[0] == 40
            assert loss_data["y_true"].shape[0] == 40
        finally:
            session.close()


class TestBenchmarkBread:
    def test_benchmark_returns_all_metrics(self):
        session = _seeded_session()
        try:
            results = benchmark_bread(session)
            metrics = {r.metric for r in results}
            assert "specific_volume_cm3_g" in metrics
            assert "crumb_hardness_n" in metrics
            assert "porosity_pct" in metrics
        finally:
            session.close()

    def test_volume_benchmark_shape(self):
        session = _seeded_session()
        try:
            results = benchmark_bread(session)
            vol_result = [r for r in results if r.metric == "specific_volume_cm3_g"][0]
            assert vol_result.n_records == 54
            assert vol_result.n_sources == 8
            assert len(vol_result.source_folds) == 8
        finally:
            session.close()

    def test_hardness_benchmark_shape(self):
        session = _seeded_session()
        try:
            results = benchmark_bread(session)
            hd_result = [r for r in results if r.metric == "crumb_hardness_n"][0]
            assert hd_result.n_records == 40
            assert hd_result.n_sources == 6
            assert len(hd_result.source_folds) == 6
        finally:
            session.close()

    def test_porosity_benchmark_shape(self):
        session = _seeded_session()
        try:
            results = benchmark_bread(session)
            por_result = [r for r in results if r.metric == "porosity_pct"][0]
            assert por_result.n_records == 11
            assert por_result.n_sources == 3
            assert len(por_result.source_folds) == 3
        finally:
            session.close()


class TestBenchmarkPasta:
    def test_pasta_benchmark(self):
        session = _seeded_session()
        try:
            results = benchmark_pasta(session)
            assert len(results) == 1
            result = results[0]
            assert result.metric == "cooking_loss_pct"
            assert result.n_records == 40
            assert result.n_sources == 3
            assert len(result.source_folds) == 3
        finally:
            session.close()


class TestBenchmarkMetrics:
    def test_compute(self):
        import numpy as np
        y_true = np.array([1.0, 2.0, 3.0, 4.0])
        y_pred = np.array([1.1, 2.1, 2.9, 4.2])
        m = BenchmarkMetrics.compute(y_true, y_pred)
        assert m.mae > 0
        assert m.rmse > 0
        assert m.r2 < 1.0
        assert abs(m.bias) < 1.0

    def test_perfect_prediction(self):
        import numpy as np
        y_true = np.array([1.0, 2.0, 3.0])
        m = BenchmarkMetrics.compute(y_true, y_true)
        assert m.mae == 0.0
        assert m.rmse == 0.0
        assert m.r2 == 1.0
        assert m.bias == 0.0
