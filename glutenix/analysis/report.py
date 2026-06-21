from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from glutenix.analysis.flavor import explain_flavor
from glutenix.db.models import SimulationCandidate


def candidate_dossier_markdown(db: Session, candidate_id: int) -> str:
    candidate = db.get(SimulationCandidate, candidate_id)
    if candidate is None:
        raise ValueError(f"Simulation candidate not found: {candidate_id}")

    run = candidate.run
    proportions = _json(candidate.proportions)
    process = _json(candidate.process)
    properties = _json(candidate.properties)
    metrics = _json(candidate.metrics)
    confidence = _json(candidate.confidence)
    risk_flags = _json(candidate.risk_flags) if candidate.risk_flags else []
    flavor = explain_flavor(db, application=run.application_name, candidate_id=candidate.id)

    lines = [
        f"# Candidate #{candidate.id} Dossier",
        "",
        "## Summary",
        "",
        f"- Application: {run.application_name}",
        f"- Run: #{run.id}",
        f"- Rank: {candidate.rank}",
        f"- Status: {candidate.status}",
        f"- Score: {_fmt(candidate.score)}",
        f"- Confidence: {confidence.get('level', 'unknown')} ({_fmt(confidence.get('score'))})",
        f"- Recommendation: {_recommendation(candidate.status, candidate.score, confidence, risk_flags)}",
        "",
        "## Run Context",
        "",
        f"- Source: {run.source}",
        f"- Preset: {run.preset or '-'}",
        f"- Seed: {run.seed if run.seed is not None else '-'}",
        f"- Samples: {_sample_text(run.blend_samples, run.process_samples)}",
        f"- Top N: {run.top_n if run.top_n is not None else '-'}",
        f"- Git commit: {run.git_commit or '-'}",
        f"- Run notes: {run.notes or '-'}",
        f"- Decision notes: {candidate.decision_notes or '-'}",
        "",
        "## Formula",
        "",
        "| Ingredient | Proportion | Percent |",
        "| --- | ---: | ---: |",
    ]

    for name, proportion in sorted(proportions.items(), key=lambda item: item[1], reverse=True):
        lines.append(f"| {name} | {_fmt(proportion, 4)} | {_fmt(proportion * 100, 2)}% |")

    lines.extend([
        "",
        "## Predicted Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ])
    for key, value in sorted(metrics.items()):
        lines.append(f"| {key} | {_fmt(value)} |")
    for key in ("protein_pct", "viscosity_index", "hydration_capacity"):
        if key in properties:
            lines.append(f"| {key} | {_fmt(properties[key])} |")
    lines.extend([
        f"| process_score | {_fmt(candidate.process_score)} |",
        f"| blend_score | {_fmt(candidate.blend_score)} |",
        f"| flavor_score | {_fmt(candidate.flavor_score)} |",
        "",
        "## Process Assumptions",
        "",
        "| Parameter | Value |",
        "| --- | ---: |",
    ])
    for key, value in sorted(process.items()):
        lines.append(f"| {key} | {_fmt(value)} |")

    lines.extend([
        "",
        "## Confidence And Evidence Notes",
        "",
        f"- Level: {confidence.get('level', 'unknown')}",
        f"- Score: {_fmt(confidence.get('score'))}",
    ])
    for key in (
        "ingredient_coverage",
        "blend_property_coverage",
        "process_coverage",
        "mechanism_coverage",
        "calibration_coverage",
    ):
        if key in confidence:
            lines.append(f"- {key}: {_fmt(confidence[key])}")
    if confidence.get("basis"):
        lines.append("- Basis:")
        lines.extend(f"  - {item}" for item in confidence["basis"])

    lines.extend([
        "",
        "## Risk Flags",
        "",
    ])
    if risk_flags:
        lines.extend(f"- {risk}" for risk in risk_flags)
    else:
        lines.append("- No saved risk flags.")

    lines.extend([
        "",
        "## Flavor Explanation",
        "",
        f"- Flavor target: {flavor['target']['name']}",
        f"- Flavor score: {_fmt(flavor['flavor_score'])}",
        f"- Evidence note: {flavor['evidence_note']}",
        "",
        "### Interpretation",
        "",
    ])
    lines.extend(f"- {item}" for item in flavor["interpretation"])

    lines.extend([
        "",
        "### Largest Flavor Gaps",
        "",
        "| Dimension | Profile | Target | Gap |",
        "| --- | ---: | ---: | ---: |",
    ])
    for dim, gap in sorted(flavor["gaps_vs_target"].items(), key=lambda item: abs(item[1]), reverse=True)[:5]:
        lines.append(
            f"| {dim} | {_fmt(flavor['profile'][dim])} | "
            f"{_fmt(flavor['target']['profile'][dim])} | {_fmt(gap)} |"
        )

    lines.extend([
        "",
        "### Ingredient Flavor Contributions",
        "",
        "| Ingredient | Proportion | Dominant dimensions | Risk |",
        "| --- | ---: | --- | --- |",
    ])
    for row in flavor["contributions"]:
        dominant = ", ".join(row["dominant_dimensions"])
        lines.append(f"| {row['ingredient']} | {_fmt(row['proportion'], 4)} | {dominant} | {row['risk']} |")

    lines.extend([
        "",
        "## Next Physical-Test Decision",
        "",
        f"- {_decision_note(candidate.status)}",
        "- Treat all predictions as pre-lab hypotheses until measured physical results are recorded.",
        "- Use the future physical-test protocol output to collect measurements with matching metric names where possible.",
        "",
    ])
    return "\n".join(lines)


def _json(payload: str | None) -> Any:
    return json.loads(payload) if payload else {}


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "-"
    if isinstance(value, int | float):
        return f"{float(value):.{digits}f}"
    if isinstance(value, list):
        return "; ".join(str(item) for item in value) or "-"
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return str(value)


def _sample_text(blend_samples: int | None, process_samples: int | None) -> str:
    if blend_samples is None and process_samples is None:
        return "-"
    return f"{blend_samples or '-'} blend x {process_samples or '-'} process"


def _recommendation(
    status: str,
    score: float,
    confidence: dict[str, Any],
    risk_flags: list[str],
) -> str:
    if status == "test_next":
        return "primary physical-test candidate"
    if status == "avoid":
        return "avoid until decision notes or risks are resolved"
    if status == "tested":
        return "already tested; review linked experiment feedback"
    if score >= 0.75 and confidence.get("level") in {"medium", "high"} and not risk_flags:
        return "promising candidate for review"
    if score >= 0.70:
        return "review risks before physical testing"
    return "low priority unless targeting a specific tradeoff"


def _decision_note(status: str) -> str:
    if status == "test_next":
        return "Current status indicates this candidate should be tested next."
    if status == "promising":
        return "Current status indicates this candidate is promising but not the next committed test."
    if status == "avoid":
        return "Current status indicates this candidate should not be tested without revisiting risks."
    if status == "tested":
        return "Current status indicates physical results should be reviewed before further action."
    return "Current status does not commit this candidate to physical testing."
