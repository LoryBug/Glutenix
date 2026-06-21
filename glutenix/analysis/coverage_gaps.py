from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from glutenix.calibration.coverage import (
    LiteratureCoverageSummary,
    assess_literature_coverage,
    build_domain_coverage,
    domain_for_application,
)
from glutenix.db.models import SimulationCandidate


EXPECTED_METRICS = {
    "Pane": ["specific_volume_cm3_g", "crumb_hardness_n", "porosity_pct", "protein_pct"],
    "Pasta fresca": ["cooking_loss_pct", "firmness_index", "water_absorption_pct", "protein_pct"],
}


def coverage_gaps_report(
    db: Session,
    *,
    application: str,
    candidate_id: int | None = None,
) -> dict[str, Any]:
    domain = domain_for_application(application)
    if domain is None:
        return {
            "application": application,
            "domain": None,
            "status": "unsupported_application",
            "summary": None,
            "expected_metrics": EXPECTED_METRICS.get(application, []),
            "metric_gaps": [],
            "limitations": [f"No structured literature coverage is available for application '{application}'."],
            "candidate": None,
        }

    summary = build_domain_coverage(db, domain)
    expected = EXPECTED_METRICS.get(summary.application, EXPECTED_METRICS.get(application, []))
    measured = set(summary.measured_metrics)
    metric_gaps = [metric for metric in expected if metric not in measured]
    report = {
        "application": summary.application,
        "domain": summary.domain,
        "status": "candidate_assessed" if candidate_id is not None else "application_summary",
        "summary": summary.as_dict(),
        "expected_metrics": expected,
        "metric_gaps": metric_gaps,
        "limitations": summary.limitations,
        "candidate": None,
    }
    if candidate_id is not None:
        report["candidate"] = _candidate_coverage(db, candidate_id, summary.application, summary)
    return report


def _candidate_coverage(
    db: Session,
    candidate_id: int,
    application: str,
    summary: LiteratureCoverageSummary,
) -> dict[str, Any]:
    candidate = db.get(SimulationCandidate, candidate_id)
    if candidate is None:
        raise ValueError(f"Simulation candidate not found: {candidate_id}")
    proportions = _json(candidate.proportions)
    properties = _numeric_values(_json(candidate.properties))
    process = _numeric_values(_json(candidate.process))
    assessment = assess_literature_coverage(
        application=application,
        ingredient_names=list(proportions),
        blend_values=properties,
        process_values=process,
        summary=summary,
    )
    covered = set(summary.covered_ingredients)
    missing_ingredients = sorted(name for name in proportions if name not in covered)
    return {
        "candidate_id": candidate.id,
        "run_id": candidate.run_id,
        "status": candidate.status,
        "score": round(candidate.score, 4),
        "assessment": assessment.as_dict(),
        "missing_ingredients": missing_ingredients,
        "risk_flags": assessment.risk_flags,
        "basis": assessment.basis,
    }


def _json(payload: str | None) -> dict[str, Any]:
    return json.loads(payload) if payload else {}


def _numeric_values(payload: dict[str, Any]) -> dict[str, float]:
    return {
        key: float(value)
        for key, value in payload.items()
        if isinstance(value, int | float) and not isinstance(value, bool)
    }
