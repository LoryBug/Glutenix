import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from glutenix.db.models import Ingredient
from glutenix.engine.blend import BlendCalculator
from glutenix.engine.cooking import PastaCookingParams, PastaCookingSimulator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PASTA_DATASET = PROJECT_ROOT / "data" / "literature" / "pasta_cooking.jsonl"


@dataclass(frozen=True)
class LiteratureRecord:
    id: str
    application: str
    source: dict[str, Any]
    literature_formula: dict[str, float]
    mapped_formula: dict[str, float]
    mapping_notes: str
    process: dict[str, Any]
    measured: dict[str, float]
    confidence: str


@dataclass(frozen=True)
class PastaCalibrationRow:
    id: str
    measured_cooking_loss_pct: float
    simulated_cooking_loss_pct: float
    corrected_cooking_loss_pct: float
    residual_before: float
    residual_after: float
    cooking_time_min: float
    formula: dict[str, float]
    source_doi: str | None


def load_literature_records(path: Path | str = DEFAULT_PASTA_DATASET) -> list[LiteratureRecord]:
    records = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            record = LiteratureRecord(**raw)
            validate_literature_record(record, line_no=line_no)
            records.append(record)
    return records


def validate_literature_record(record: LiteratureRecord, line_no: int | None = None) -> None:
    where = f" at line {line_no}" if line_no is not None else ""
    if not record.id:
        raise ValueError(f"Record id is required{where}")
    if "cooking_loss_pct" not in record.measured:
        raise ValueError(f"measured.cooking_loss_pct is required{where}")
    if record.measured["cooking_loss_pct"] < 0:
        raise ValueError(f"measured.cooking_loss_pct must be non-negative{where}")
    if "cooking_time_min" not in record.process:
        raise ValueError(f"process.cooking_time_min is required{where}")
    total = sum(record.mapped_formula.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"mapped_formula must sum to 1.0, got {total}{where}")


def _metrics(measured: list[float], predicted: list[float]) -> dict[str, float]:
    if len(measured) != len(predicted):
        raise ValueError("measured and predicted lengths differ")
    if not measured:
        return {"mae": 0.0, "rmse": 0.0, "bias": 0.0}
    errors = [p - m for p, m in zip(predicted, measured)]
    return {
        "mae": round(mean(abs(e) for e in errors), 4),
        "rmse": round(float(np.sqrt(mean(e * e for e in errors))), 4),
        "bias": round(mean(errors), 4),
    }


def _fit_linear_correction(predicted: list[float], measured: list[float]) -> tuple[float, float]:
    if len(predicted) < 2 or max(predicted) - min(predicted) < 1e-9:
        return 0.0, 1.0
    beta, alpha = np.polyfit(predicted, measured, deg=1)
    return float(alpha), float(beta)


def _blend_data_from_record(record: LiteratureRecord, db: Session):
    ingredients = {ing.name: ing for ing in db.query(Ingredient).all()}
    blend_data = []
    missing = []
    for name, proportion in record.mapped_formula.items():
        ingredient = ingredients.get(name)
        if ingredient is None:
            missing.append(name)
            continue
        blend_data.append((ingredient, proportion))
    if missing:
        raise ValueError(f"Missing mapped ingredients for {record.id}: {missing}")
    return blend_data


def compare_pasta_cooking_records(
    db: Session,
    records: list[LiteratureRecord] | None = None,
) -> dict[str, Any]:
    records = records or load_literature_records()
    calc = BlendCalculator()
    measured = []
    predicted = []
    raw_rows = []

    for record in records:
        blend_data = _blend_data_from_record(record, db)
        props = calc.calculate(blend_data)
        result = PastaCookingSimulator(
            PastaCookingParams(
                water_temp_c=float(record.process.get("water_temp_c", 98.0)),
                cooking_time_min=float(record.process["cooking_time_min"]),
                pasta_thickness_mm=float(record.process.get("pasta_thickness_mm", 2.0)),
            )
        ).simulate(props)
        measured_loss = float(record.measured["cooking_loss_pct"])
        measured.append(measured_loss)
        predicted.append(result.cooking_loss_pct)
        raw_rows.append((record, measured_loss, result.cooking_loss_pct))

    alpha, beta = _fit_linear_correction(predicted, measured)
    corrected = [alpha + beta * value for value in predicted]
    rows = []
    for (record, measured_loss, simulated_loss), corrected_loss in zip(raw_rows, corrected):
        rows.append(PastaCalibrationRow(
            id=record.id,
            measured_cooking_loss_pct=round(measured_loss, 4),
            simulated_cooking_loss_pct=round(simulated_loss, 4),
            corrected_cooking_loss_pct=round(corrected_loss, 4),
            residual_before=round(simulated_loss - measured_loss, 4),
            residual_after=round(corrected_loss - measured_loss, 4),
            cooking_time_min=float(record.process["cooking_time_min"]),
            formula=record.mapped_formula,
            source_doi=record.source.get("doi"),
        ))

    return {
        "n_records": len(records),
        "metric": "cooking_loss_pct",
        "source_count": len({record.source.get("doi") for record in records}),
        "correction": {"alpha": round(alpha, 6), "beta": round(beta, 6)},
        "before": _metrics(measured, predicted),
        "after": _metrics(measured, corrected),
        "rows": [row.__dict__ for row in rows],
        "limitations": [
            "Amaranth is mapped to quinoa flour proxy because amaranth is not in the DB.",
            "Sodium alginate is mapped to xanthan gum proxy because alginate is not in the DB.",
            "Dataset currently contains only cooking loss examples from one paper.",
            "Linear correction is diagnostic; do not treat as calibrated production model yet.",
        ],
    }


def pasta_calibration_report_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Pasta Cooking Literature Calibration Report",
        "",
        f"Records: {result['n_records']}",
        f"Metric: `{result['metric']}`",
        f"Sources: {result['source_count']}",
        "",
        "## Error Summary",
        "",
        "| Stage | MAE | RMSE | Bias |",
        "|---|---:|---:|---:|",
        f"| Before correction | {result['before']['mae']} | {result['before']['rmse']} | {result['before']['bias']} |",
        f"| After linear correction | {result['after']['mae']} | {result['after']['rmse']} | {result['after']['bias']} |",
        "",
        "## Linear Correction",
        "",
        "```text",
        f"corrected = {result['correction']['alpha']} + {result['correction']['beta']} * simulated",
        "```",
        "",
        "## Rows",
        "",
        "| ID | Time min | Measured | Simulated | Corrected | Residual Before | Residual After |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["rows"]:
        lines.append(
            f"| {row['id']} | {row['cooking_time_min']} | {row['measured_cooking_loss_pct']} | "
            f"{row['simulated_cooking_loss_pct']} | {row['corrected_cooking_loss_pct']} | "
            f"{row['residual_before']} | {row['residual_after']} |"
        )
    lines.extend([
        "",
        "## Limitations",
        "",
    ])
    lines.extend(f"- {item}" for item in result["limitations"])
    lines.append("")
    return "\n".join(lines)
