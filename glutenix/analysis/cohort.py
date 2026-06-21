from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from glutenix.db.models import SimulationCandidate, SimulationRun


@dataclass(frozen=True)
class CohortFilters:
    application: str | None = None
    preset: str | None = None
    statuses: tuple[str, ...] = ()
    run_ids: tuple[int, ...] = ()
    max_rank: int | None = None
    limit: int | None = None


def analyze_candidate_cohort(db: Session, filters: CohortFilters) -> dict[str, Any]:
    candidates = _candidate_query(db, filters)
    if filters.limit is not None:
        candidates = candidates[:filters.limit]

    status_counts: Counter[str] = Counter()
    preset_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    ingredient_values: dict[str, list[float]] = defaultdict(list)
    metric_values: dict[str, list[float]] = defaultdict(list)
    top_candidates = []

    for candidate in candidates:
        run = candidate.run
        status_counts[candidate.status] += 1
        preset_counts[run.preset or "-"] += 1
        source_counts[run.source] += 1

        for name, value in _json(candidate.proportions).items():
            if isinstance(value, int | float):
                ingredient_values[name].append(float(value))
        for key, value in _numeric_candidate_values(candidate).items():
            metric_values[key].append(value)
        top_candidates.append({
            "candidate_id": candidate.id,
            "run_id": candidate.run_id,
            "rank": candidate.rank,
            "status": candidate.status,
            "preset": run.preset,
            "score": round(candidate.score, 4),
        })

    top_candidates.sort(key=lambda row: row["score"], reverse=True)
    return {
        "filters": {
            "application": filters.application,
            "preset": filters.preset,
            "statuses": list(filters.statuses),
            "run_ids": list(filters.run_ids),
            "max_rank": filters.max_rank,
            "limit": filters.limit,
        },
        "candidate_count": len(candidates),
        "run_count": len({candidate.run_id for candidate in candidates}),
        "status_counts": dict(sorted(status_counts.items())),
        "preset_counts": dict(sorted(preset_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "ingredients": _summary_map(ingredient_values, scale=100.0),
        "metrics": _summary_map(metric_values),
        "top_candidates": top_candidates[:10],
    }


def _candidate_query(db: Session, filters: CohortFilters) -> list[SimulationCandidate]:
    query = db.query(SimulationCandidate).join(SimulationRun)
    if filters.application:
        query = query.filter(SimulationRun.application_name == filters.application)
    if filters.preset:
        query = query.filter(SimulationRun.preset == filters.preset)
    if filters.statuses:
        query = query.filter(SimulationCandidate.status.in_(filters.statuses))
    if filters.run_ids:
        query = query.filter(SimulationCandidate.run_id.in_(filters.run_ids))
    if filters.max_rank is not None:
        query = query.filter(SimulationCandidate.rank <= filters.max_rank)
    return query.order_by(SimulationCandidate.score.desc(), SimulationCandidate.id.asc()).all()


def _numeric_candidate_values(candidate: SimulationCandidate) -> dict[str, float]:
    values: dict[str, float] = {
        "score": float(candidate.score),
    }
    for key in ("process_score", "blend_score", "flavor_score"):
        value = getattr(candidate, key)
        if value is not None:
            values[key] = float(value)
    for payload in (_json(candidate.properties), _json(candidate.metrics)):
        for key, value in payload.items():
            if isinstance(value, int | float):
                values[key] = float(value)
    return values


def _summary_map(values_by_key: dict[str, list[float]], scale: float = 1.0) -> dict[str, dict[str, float | int]]:
    rows = {
        key: _summary([value * scale for value in values])
        for key, values in values_by_key.items()
        if values
    }
    return dict(sorted(rows.items()))


def _summary(values: list[float]) -> dict[str, float | int]:
    values = sorted(values)
    return {
        "count": len(values),
        "min": round(values[0], 4),
        "max": round(values[-1], 4),
        "mean": round(sum(values) / len(values), 4),
    }


def _json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    parsed = json.loads(value)
    return parsed if isinstance(parsed, dict) else {}
