from __future__ import annotations

import json
import math
from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from glutenix.db.models import ExperimentResult, SimulationCandidate, SimulationRun


def candidate_feedback(db: Session, candidate_id: int) -> dict[str, Any]:
    candidate = db.get(SimulationCandidate, candidate_id)
    if candidate is None:
        raise ValueError(f"Simulation candidate not found: {candidate_id}")
    experiments = _linked_experiments(db, candidate_id)
    predicted = _predicted_numeric_values(candidate)
    comparisons = []
    for experiment in experiments:
        for metric, measured in _json(experiment.metrics).items():
            if metric not in predicted or not isinstance(measured, int | float) or isinstance(measured, bool):
                continue
            predicted_value = predicted[metric]
            absolute_delta = float(measured) - predicted_value
            percent_delta = None if predicted_value == 0 else absolute_delta / predicted_value * 100
            comparisons.append({
                "metric": metric,
                "predicted": round(predicted_value, 4),
                "measured": round(float(measured), 4),
                "absolute_delta": round(absolute_delta, 4),
                "percent_delta": None if percent_delta is None else round(percent_delta, 2),
            })
    return {
        "candidate_id": candidate.id,
        "run_id": candidate.run_id,
        "status": candidate.status,
        "experiment_count": len(experiments),
        "comparisons": comparisons,
        "summary": _candidate_feedback_summary(experiments, comparisons),
        "evidence_note": "Candidate feedback is diagnostic only; it does not recalibrate heuristic models automatically.",
    }


def experimental_feedback_summary(db: Session, application: str | None = None) -> dict[str, Any]:
    candidates = _candidate_map(db, application)
    linked_experiments: dict[int, list[ExperimentResult]] = defaultdict(list)
    comparisons = []
    unmatched: dict[str, int] = defaultdict(int)

    for experiment in db.query(ExperimentResult).order_by(ExperimentResult.created_at.asc(), ExperimentResult.id.asc()).all():
        conditions = _json(experiment.conditions)
        candidate_id = conditions.get("candidate_id")
        if not isinstance(candidate_id, int) or candidate_id not in candidates:
            continue
        linked_experiments[candidate_id].append(experiment)
        predicted = _predicted_numeric_values(candidates[candidate_id])
        for metric, measured in _json(experiment.metrics).items():
            if not isinstance(measured, int | float) or isinstance(measured, bool):
                continue
            if metric not in predicted:
                unmatched[metric] += 1
                continue
            predicted_value = predicted[metric]
            measured_value = float(measured)
            absolute_delta = measured_value - predicted_value
            percent_delta = None if predicted_value == 0 else absolute_delta / predicted_value * 100
            comparisons.append({
                "candidate_id": candidate_id,
                "run_id": candidates[candidate_id].run_id,
                "experiment_id": experiment.id,
                "metric": metric,
                "predicted": predicted_value,
                "measured": measured_value,
                "absolute_delta": absolute_delta,
                "percent_delta": percent_delta,
            })

    linked_experiment_count = sum(len(items) for items in linked_experiments.values())
    if linked_experiment_count == 0:
        status = "no_experiments"
        message = "No linked experiment results were found for the selected candidates."
    elif not comparisons:
        status = "no_comparable_metrics"
        message = "Linked experiments exist, but no measured numeric metric names match saved predictions."
    else:
        status = "compared"
        message = "Measured physical results were aggregated against saved simulation predictions."

    return {
        "application": application,
        "status": status,
        "message": message,
        "candidate_count": len(candidates),
        "linked_candidate_count": len(linked_experiments),
        "linked_experiment_count": linked_experiment_count,
        "comparison_count": len(comparisons),
        "metrics": _metric_summaries(comparisons),
        "candidates": _candidate_summaries(candidates, linked_experiments, comparisons),
        "unmatched_measurements": dict(sorted(unmatched.items())),
        "evidence_note": "Feedback summary is diagnostic only; it does not recalibrate heuristic models automatically.",
    }


def _candidate_map(db: Session, application: str | None) -> dict[int, SimulationCandidate]:
    query = db.query(SimulationCandidate)
    if application:
        query = query.join(SimulationCandidate.run).filter(SimulationRun.application_name == application)
    return {candidate.id: candidate for candidate in query.all()}


def _linked_experiments(db: Session, candidate_id: int) -> list[ExperimentResult]:
    linked = []
    for experiment in db.query(ExperimentResult).order_by(ExperimentResult.created_at.desc(), ExperimentResult.id.desc()).all():
        conditions = _json(experiment.conditions)
        if conditions.get("candidate_id") == candidate_id:
            linked.append(experiment)
    return linked


def _candidate_feedback_summary(
    experiments: list[ExperimentResult],
    comparisons: list[dict[str, Any]],
) -> dict[str, Any]:
    if not experiments:
        return {
            "status": "no_experiments",
            "message": "No physical test results are linked to this candidate yet.",
        }
    if not comparisons:
        return {
            "status": "no_comparable_metrics",
            "message": "Linked experiments exist, but no measured metric names match predicted numeric fields.",
        }
    abs_pct = [abs(item["percent_delta"]) for item in comparisons if item["percent_delta"] is not None]
    mean_abs_percent_delta = None if not abs_pct else round(sum(abs_pct) / len(abs_pct), 2)
    largest = max(comparisons, key=lambda item: abs(item["absolute_delta"]))
    return {
        "status": "compared",
        "message": "Measured physical results were compared against saved simulation predictions.",
        "experiment_count": len(experiments),
        "metric_count": len(comparisons),
        "mean_abs_percent_delta": mean_abs_percent_delta,
        "largest_absolute_delta": largest,
    }


def _metric_summaries(comparisons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for metric in sorted({row["metric"] for row in comparisons}):
        metric_rows = [row for row in comparisons if row["metric"] == metric]
        errors = [row["absolute_delta"] for row in metric_rows]
        abs_errors = [abs(value) for value in errors]
        pct_errors = [abs(row["percent_delta"]) for row in metric_rows if row["percent_delta"] is not None]
        rows.append({
            "metric": metric,
            "count": len(metric_rows),
            "candidate_count": len({row["candidate_id"] for row in metric_rows}),
            "experiment_count": len({row["experiment_id"] for row in metric_rows}),
            "mean_predicted": _rounded_mean(row["predicted"] for row in metric_rows),
            "mean_measured": _rounded_mean(row["measured"] for row in metric_rows),
            "mean_error": _rounded_mean(errors),
            "mae": _rounded_mean(abs_errors),
            "rmse": round(math.sqrt(sum(value * value for value in errors) / len(errors)), 4),
            "mape_pct": None if not pct_errors else _rounded_mean(pct_errors),
        })
    return rows


def _candidate_summaries(
    candidates: dict[int, SimulationCandidate],
    linked_experiments: dict[int, list[ExperimentResult]],
    comparisons: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for candidate_id, experiments in sorted(linked_experiments.items()):
        candidate = candidates[candidate_id]
        candidate_rows = [row for row in comparisons if row["candidate_id"] == candidate_id]
        pct_errors = [abs(row["percent_delta"]) for row in candidate_rows if row["percent_delta"] is not None]
        rows.append({
            "candidate_id": candidate.id,
            "run_id": candidate.run_id,
            "status": candidate.status,
            "score": round(candidate.score, 4),
            "experiment_count": len(experiments),
            "comparison_count": len(candidate_rows),
            "mean_abs_percent_delta": None if not pct_errors else _rounded_mean(pct_errors),
        })
    return rows


def _predicted_numeric_values(candidate: SimulationCandidate) -> dict[str, float]:
    values: dict[str, float] = {}
    for payload in (
        _json(candidate.metrics),
        _json(candidate.properties),
        {
            "score": candidate.score,
            "process_score": candidate.process_score,
            "blend_score": candidate.blend_score,
            "flavor_score": candidate.flavor_score,
        },
    ):
        for key, value in payload.items():
            if isinstance(value, int | float) and not isinstance(value, bool):
                values[key] = float(value)
    return values


def _json(payload: str | None) -> dict[str, Any]:
    return json.loads(payload) if payload else {}


def _rounded_mean(values: Any) -> float:
    items = list(values)
    return round(sum(items) / len(items), 4)
