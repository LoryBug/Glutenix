"""Classical ML residual models for heuristic simulator error correction.

Scope:
- Ridge regression (linear residual)
- RandomForest regression (non-linear residual)
- Leave-one-source-out cross-validation for DOI estimation

Design notes:
- Models predict residual = measured - simulated, not the absolute value.
- Feature vector = BlendProperties features + process parameters.
- This is diagnostic only. No production calibration is applied.
- DL is explicitly deferred until more records exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import structlog
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from glutenix.calibration.literature import (
    DEFAULT_BREAD_DATASET,
    DEFAULT_PASTA_DATASET,
    LiteratureRecord,
    _bread_process_family,
    _blend_data_from_record,
    _record_bread_params,
    _record_cooking_params,
    _source_label,
    load_literature_records,
)
from glutenix.engine.blend import BlendCalculator, BlendProperties
from glutenix.engine.bread import BreadQualitySimulator
from glutenix.engine.cooking import PastaCookingSimulator

logger = structlog.get_logger("glutenix.ml.residual")

RANDOM_SEED = 42

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkMetrics:
    rmse: float
    mae: float
    r2: float
    bias: float

    @classmethod
    def compute(cls, y_true: np.ndarray, y_pred: np.ndarray) -> BenchmarkMetrics:
        errors = y_pred - y_true
        return cls(
            rmse=float(np.sqrt(mean_squared_error(y_true, y_pred))),
            mae=float(mean_absolute_error(y_true, y_pred)),
            r2=float(r2_score(y_true, y_pred)),
            bias=float(np.mean(errors)),
        )


# ---------------------------------------------------------------------------
# Per-fold and overall results
# ---------------------------------------------------------------------------


@dataclass
class SourceFoldResult:
    """Metrics for one leave-one-source-out fold."""

    source: str
    n_train: int
    n_test: int
    heuristic_metrics: BenchmarkMetrics
    ridge_metrics: BenchmarkMetrics | None = None
    rf_metrics: BenchmarkMetrics | None = None


@dataclass
class BenchmarkResult:
    metric: str
    domain: str
    n_records: int
    n_sources: int
    heuristic_overall: BenchmarkMetrics
    ridge_overall: BenchmarkMetrics | None = None
    rf_overall: BenchmarkMetrics | None = None
    source_folds: list[SourceFoldResult] = field(default_factory=list)
    ridge_improvement_pct: float | None = None
    rf_improvement_pct: float | None = None


# ---------------------------------------------------------------------------
# Feature extraction from heuristic simulation
# ---------------------------------------------------------------------------

BLEND_FEATURES = [
    "protein_pct",
    "starch_pct",
    "fat_pct",
    "fiber_pct",
    "water_absorption",
    "gelatinization_temp_min",
    "amylose_pct",
    "viscosity_index",
    "hydrocolloid_pct",
]

BREAD_PROCESS_FEATURES = [
    "hydration_pct",
    "fermentation_temp_c",
    "fermentation_time_min",
    "baking_temp_c",
    "baking_time_min",
    "yeast_pct",
    "sugar_pct",
    "fat_pct",
    "chemical_leavening_pct",
    "emulsifier_pct",
    "tg_pct",
    "storage_days",
]

PASTA_PROCESS_FEATURES = [
    "water_temp_c",
    "cooking_time_min",
    "pasta_thickness_mm",
    "calcium_lactate_m",
    "calcium_bath_time_min",
    "dough_heat_temp_c",
    "dough_heat_time_min",
    "dried_pasta",
    "water_to_flour_ratio",
    "extrusion_moisture_pct",
]


def _extract_blend_features(props: BlendProperties) -> list[float]:
    return [getattr(props, f) for f in BLEND_FEATURES]


def _extract_bread_process(record: LiteratureRecord) -> list[float]:
    p = record.process
    return [
        float(p.get("hydration_pct", 100.0)),
        float(p.get("fermentation_temp_c", 30.0)),
        float(p.get("fermentation_time_min", 60.0)),
        float(p.get("baking_temp_c", 190.0)),
        float(p.get("baking_time_min", 40.0)),
        float(p.get("yeast_pct", 3.0)),
        float(p.get("sugar_pct", 3.0)),
        float(p.get("fat_pct", 0.0)),
        float(p.get("chemical_leavening_pct", 0.0)),
        float(p.get("emulsifier_pct", 0.0)),
        float(p.get("tg_pct", 0.0)),
        float(p.get("storage_days", 1.0)),
    ]


def _extract_pasta_process(record: LiteratureRecord) -> list[float]:
    p = record.process
    water_to_flour = _parse_water_ratio(p.get("flour_water_ratio"))
    features = [
        float(p.get("water_temp_c", 98.0)),
        float(p.get("cooking_time_min", 6.0)),
        float(p.get("pasta_thickness_mm", 2.0)),
        float(p.get("calcium_lactate_m", 0.0)),
        float(p.get("calcium_bath_time_min", 0.0)),
        float(p.get("dough_heat_temp_c", 0.0)),
        float(p.get("dough_heat_time_min", 0.0)),
        float(p.get("dried_pasta", False)),
        water_to_flour,
    ]
    if p.get("extrusion_moisture_pct") is not None:
        features.append(float(p["extrusion_moisture_pct"]))
    else:
        features.append(32.0)
    return features


def _parse_water_ratio(value: Any) -> float:
    if value is None:
        return 3.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if ":" in text:
        parts = text.split(":", 1)
        try:
            return float(parts[1].strip()) / float(parts[0].strip())
        except (ValueError, ZeroDivisionError):
            return 3.0
    return 3.0


# ---------------------------------------------------------------------------
# Build feature matrices
# ---------------------------------------------------------------------------


def _compute_bread_row(
    record: LiteratureRecord, calc: BlendCalculator, db_session: Any
) -> dict[str, Any] | None:
    """Run bread simulator on one record, return feature vector + targets."""
    try:
        blend_data = _blend_data_from_record(record, db_session)
    except ValueError as exc:
        logger.warning("skip_record_missing_ingredients", id=record.id, error=str(exc))
        return None
    props = calc.calculate(blend_data)
    result = BreadQualitySimulator(_record_bread_params(record)).simulate(props)
    blend_feats = _extract_blend_features(props)
    process_feats = _extract_bread_process(record)
    features = blend_feats + process_feats

    targets: dict[str, float] = {}
    if "specific_volume_cm3_g" in record.measured:
        targets["specific_volume_cm3_g"] = float(record.measured["specific_volume_cm3_g"])
    if "crumb_hardness_n" in record.measured:
        targets["crumb_hardness_n"] = float(record.measured["crumb_hardness_n"])
    if "porosity_pct" in record.measured:
        targets["porosity_pct"] = float(record.measured["porosity_pct"])

    return {
        "id": record.id,
        "source": _source_label(record),
        "family": _bread_process_family(record),
        "features": features,
        "measured": targets,
        "simulated": {
            "specific_volume_cm3_g": result.specific_volume_cm3_g,
            "crumb_hardness_n": result.crumb_hardness_n,
            "porosity_pct": result.porosity_pct,
        },
    }


def _compute_pasta_row(
    record: LiteratureRecord, calc: BlendCalculator, db_session: Any
) -> dict[str, Any] | None:
    """Run pasta simulator on one record, return feature vector + targets."""
    try:
        blend_data = _blend_data_from_record(record, db_session)
    except ValueError as exc:
        logger.warning("skip_record_missing_ingredients", id=record.id, error=str(exc))
        return None
    props = calc.calculate(blend_data)
    result = PastaCookingSimulator(_record_cooking_params(record)).simulate(props)
    blend_feats = _extract_blend_features(props)
    process_feats = _extract_pasta_process(record)
    features = blend_feats + process_feats

    targets: dict[str, float] = {}
    if "cooking_loss_pct" in record.measured:
        targets["cooking_loss_pct"] = float(record.measured["cooking_loss_pct"])

    return {
        "id": record.id,
        "source": _source_label(record),
        "family": result.process_family,
        "features": features,
        "measured": targets,
        "simulated": {
            "cooking_loss_pct": result.cooking_loss_pct,
        },
    }


def build_bread_dataset(db_session, records: list[LiteratureRecord] | None = None) -> dict[str, Any]:
    """Build full bread feature matrix and targets for all metrics."""
    if records is None:
        records = load_literature_records(
            DEFAULT_BREAD_DATASET,
            required_measured_metrics=(),
            required_process_fields=("hydration_pct", "baking_time_min"),
        )
    calc = BlendCalculator()
    rows = []
    for record in records:
        row = _compute_bread_row(record, calc, db_session)
        if row is not None:
            rows.append(row)

    X = np.array([r["features"] for r in rows])

    metric_keys = ["specific_volume_cm3_g", "crumb_hardness_n", "porosity_pct"]
    datasets: dict[str, dict[str, Any]] = {}
    for metric in metric_keys:
        valid = [(i, r) for i, r in enumerate(rows) if metric in r["measured"]]
        if not valid:
            continue
        idx = np.array([v[0] for v in valid])
        targets = np.array([v[1]["measured"][metric] for v in valid])
        simulated = np.array([v[1]["simulated"][metric] for v in valid])
        residuals = targets - simulated
        sources = [v[1]["source"] for v in valid]
        families = [v[1]["family"] for v in valid]

        datasets[metric] = {
            "X": X[idx],
            "y_true": targets,
            "y_sim": simulated,
            "residual": residuals,
            "sources": sources,
            "families": families,
            "ids": [v[1]["id"] for v in valid],
        }

    return {
        "rows": rows,
        "dataset": datasets,
        "n_records": len(rows),
        "feature_names": BLEND_FEATURES + BREAD_PROCESS_FEATURES,
    }


def build_pasta_dataset(db_session, records: list[LiteratureRecord] | None = None) -> dict[str, Any]:
    """Build full pasta feature matrix and residual targets."""
    if records is None:
        records = load_literature_records(DEFAULT_PASTA_DATASET)
    calc = BlendCalculator()
    rows = []
    for record in records:
        row = _compute_pasta_row(record, calc, db_session)
        if row is not None:
            rows.append(row)

    X = np.array([r["features"] for r in rows])
    metric = "cooking_loss_pct"
    targets = np.array([r["measured"][metric] for r in rows])
    simulated = np.array([r["simulated"][metric] for r in rows])
    residuals = targets - simulated
    sources = [r["source"] for r in rows]
    families = [r["family"] for r in rows]

    return {
        "rows": rows,
        "dataset": {
            metric: {
                "X": X,
                "y_true": targets,
                "y_sim": simulated,
                "residual": residuals,
                "sources": sources,
                "families": families,
                "ids": [r["id"] for r in rows],
            }
        },
        "n_records": len(rows),
        "feature_names": BLEND_FEATURES + PASTA_PROCESS_FEATURES,
    }


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------


def _run_cv_benchmark(
    X: np.ndarray,
    y_true: np.ndarray,
    y_sim: np.ndarray,
    sources: list[str],
    metric: str,
    domain: str,
    ridge_kwargs: dict[str, Any] | None = None,
    rf_kwargs: dict[str, Any] | None = None,
) -> BenchmarkResult:
    """Run leave-one-source-out CV for ridge and RandomForest residual models."""
    residues = y_true - y_sim
    logo = LeaveOneGroupOut()
    groups = np.array(sources)
    unique_sources = sorted(set(sources))

    ridge_preds = np.full_like(y_true, np.nan)
    rf_preds = np.full_like(y_true, np.nan)
    fold_results: list[SourceFoldResult] = []

    for train_idx, test_idx in logo.split(X, y_true, groups=groups):
        source_held_out = sources[test_idx[0]]
        X_tr, X_te = X[train_idx], X[test_idx]
        res_tr = residues[train_idx]
        y_te = y_true[test_idx]
        y_sim_te = y_sim[test_idx]

        heuristic_metrics = BenchmarkMetrics.compute(y_te, y_sim_te)

        fold = SourceFoldResult(
            source=source_held_out,
            n_train=len(train_idx),
            n_test=len(test_idx),
            heuristic_metrics=heuristic_metrics,
        )

        if len(train_idx) >= 5:
            ridge_m = make_pipeline(StandardScaler(), Ridge(alpha=1.0, random_state=RANDOM_SEED))
            if ridge_kwargs:
                ridge_m = make_pipeline(StandardScaler(), Ridge(**ridge_kwargs))
            ridge_m.fit(X_tr, res_tr)
            ridge_res = ridge_m.predict(X_te)
            ridge_preds[test_idx] = y_sim_te + ridge_res
            fold.ridge_metrics = BenchmarkMetrics.compute(y_te, ridge_preds[test_idx])

            rf_m = RandomForestRegressor(
                n_estimators=100, max_depth=5, random_state=RANDOM_SEED
            )
            if rf_kwargs:
                rf_m = RandomForestRegressor(**rf_kwargs)
            rf_m.fit(X_tr, res_tr)
            rf_res = rf_m.predict(X_te)
            rf_preds[test_idx] = y_sim_te + rf_res
            fold.rf_metrics = BenchmarkMetrics.compute(y_te, rf_preds[test_idx])

        fold_results.append(fold)

    heuristic_overall = BenchmarkMetrics.compute(y_true, y_sim)

    ridge_valid = ridge_preds[~np.isnan(ridge_preds)]
    ridge_overall = None
    if len(ridge_valid) > 0:
        ridge_overall = BenchmarkMetrics.compute(y_true[~np.isnan(ridge_preds)], ridge_preds[~np.isnan(ridge_preds)])

    rf_valid = rf_preds[~np.isnan(rf_preds)]
    rf_overall = None
    if len(rf_valid) > 0:
        rf_overall = BenchmarkMetrics.compute(y_true[~np.isnan(rf_preds)], rf_preds[~np.isnan(rf_preds)])

    ridge_improvement = None
    if ridge_overall is not None and heuristic_overall.mae > 0:
        ridge_improvement = (
            (heuristic_overall.mae - ridge_overall.mae) / heuristic_overall.mae * 100
        )

    rf_improvement = None
    if rf_overall is not None and heuristic_overall.mae > 0:
        rf_improvement = (
            (heuristic_overall.mae - rf_overall.mae) / heuristic_overall.mae * 100
        )

    return BenchmarkResult(
        metric=metric,
        domain=domain,
        n_records=len(y_true),
        n_sources=len(unique_sources),
        heuristic_overall=heuristic_overall,
        ridge_overall=ridge_overall,
        rf_overall=rf_overall,
        source_folds=fold_results,
        ridge_improvement_pct=round(ridge_improvement, 2) if ridge_improvement is not None else None,
        rf_improvement_pct=round(rf_improvement, 2) if rf_improvement is not None else None,
    )


def benchmark_bread(
    db_session,
    records: list[LiteratureRecord] | None = None,
) -> list[BenchmarkResult]:
    """Run benchmark on all bread metrics with LOOSO-CV."""
    dataset = build_bread_dataset(db_session, records)
    results = []
    for metric, data in dataset["dataset"].items():
        logger.info(
            "benchmark_bread_metric",
            metric=metric,
            n_records=len(data["y_true"]),
            n_sources=len(set(data["sources"])),
        )
        result = _run_cv_benchmark(
            X=data["X"],
            y_true=data["y_true"],
            y_sim=data["y_sim"],
            sources=data["sources"],
            metric=metric,
            domain="bread",
        )
        results.append(result)
    return results


def benchmark_pasta(
    db_session,
    records: list[LiteratureRecord] | None = None,
) -> list[BenchmarkResult]:
    """Run benchmark on pasta cooking_loss with LOOSO-CV."""
    dataset = build_pasta_dataset(db_session, records)
    results = []
    for metric, data in dataset["dataset"].items():
        logger.info(
            "benchmark_pasta_metric",
            metric=metric,
            n_records=len(data["y_true"]),
            n_sources=len(set(data["sources"])),
        )
        result = _run_cv_benchmark(
            X=data["X"],
            y_true=data["y_true"],
            y_sim=data["y_sim"],
            sources=data["sources"],
            metric=metric,
            domain="pasta",
        )
        results.append(result)
    return results
