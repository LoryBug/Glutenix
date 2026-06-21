from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from glutenix.applications.workflow import expected_metrics_for_application
from glutenix.calibration.coverage import (
    LiteratureCoverageSummary,
    assess_literature_coverage,
    build_domain_coverage,
    domain_for_application,
)
from glutenix.calibration.pizza_v1 import assess_pizza_v1_coverage, is_pizza_v1_application
from glutenix.db.models import SimulationCandidate


def coverage_gaps_report(
    db: Session,
    *,
    application: str,
    candidate_id: int | None = None,
) -> dict[str, Any]:
    domain = domain_for_application(application)
    if domain is None:
        if is_pizza_v1_application(application):
            return _pizza_v1_report(db, application=application, candidate_id=candidate_id)
        return {
            "application": application,
            "domain": None,
            "status": "unsupported_application",
            "summary": None,
            "expected_metrics": expected_metrics_for_application(application),
            "metric_gaps": [],
            "limitations": [f"No structured literature coverage is available for application '{application}'."],
            "candidate": None,
        }

    summary = build_domain_coverage(db, domain)
    expected = expected_metrics_for_application(summary.application) or expected_metrics_for_application(application)
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


def _pizza_v1_report(
    db: Session,
    *,
    application: str,
    candidate_id: int | None,
) -> dict[str, Any]:
    report = {
        "application": application,
        "domain": "pizza_v1_audit",
        "status": "candidate_assessed" if candidate_id is not None else "application_summary",
        "summary": None,
        "expected_metrics": expected_metrics_for_application(application),
        "metric_gaps": expected_metrics_for_application(application),
        "limitations": [
            "Pizza V1 uses audit-boundary diagnostics only; no structured pizza_baking dataset exists yet.",
            "Coverage diagnostics are based on docs/pizza-v1-literature-audit.md, not calibration error.",
        ],
        "candidate": None,
        "coverage_diagnostics": None,
    }
    if candidate_id is None:
        return report

    candidate = db.get(SimulationCandidate, candidate_id)
    if candidate is None:
        raise ValueError(f"Simulation candidate not found: {candidate_id}")
    proportions = _json(candidate.proportions)
    diagnostics = assess_pizza_v1_coverage(
        ingredient_names=list(proportions),
        blend_values=_numeric_values(_json(candidate.properties)),
        process_values=_numeric_values(_json(candidate.process)),
    )
    report["coverage_diagnostics"] = diagnostics.as_dict()
    report["candidate"] = {
        "candidate_id": candidate.id,
        "run_id": candidate.run_id,
        "status": candidate.status,
        "score": round(candidate.score, 4),
        "assessment": diagnostics.as_literature_coverage(),
        "missing_ingredients": [
            item[11:]
            for item in diagnostics.unsupported_variables
            if item.startswith("ingredient:")
        ],
        "risk_flags": diagnostics.risk_flags,
        "basis": diagnostics.basis,
    }
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
