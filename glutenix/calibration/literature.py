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
VALID_CONFIDENCE_LEVELS = {"low", "medium", "high"}


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
    water_to_flour_ratio: float | None
    process_family: str
    formula: dict[str, float]
    source_doi: str | None
    source_label: str
    measured_water_absorption_pct: float | None
    simulated_water_absorption_pct: float | None
    measured_swelling_index: float | None
    simulated_swelling_index: float | None
    gelation_index: float
    pregelatinization_index: float
    syneresis_index: float
    starch_leaching_index: float


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
    if not record.application:
        raise ValueError(f"application is required{where}")
    if not record.source:
        raise ValueError(f"source is required{where}")
    if not record.source.get("title"):
        raise ValueError(f"source.title is required{where}")
    if not any(record.source.get(key) for key in ("doi", "pmcid", "url")):
        raise ValueError(f"source must include doi, pmcid, or url{where}")
    if not record.literature_formula:
        raise ValueError(f"literature_formula is required{where}")
    if not record.mapped_formula:
        raise ValueError(f"mapped_formula is required{where}")
    if record.confidence not in VALID_CONFIDENCE_LEVELS:
        raise ValueError(f"confidence must be one of {sorted(VALID_CONFIDENCE_LEVELS)}{where}")
    for field_name, formula in (
        ("literature_formula", record.literature_formula),
        ("mapped_formula", record.mapped_formula),
    ):
        for name, value in formula.items():
            if not name:
                raise ValueError(f"{field_name} ingredient names must be non-empty{where}")
            if not np.isfinite(value) or value <= 0:
                raise ValueError(f"{field_name}.{name} must be a positive finite value{where}")
    if "cooking_loss_pct" not in record.measured:
        raise ValueError(f"measured.cooking_loss_pct is required{where}")
    for name, value in record.measured.items():
        if not np.isfinite(value):
            raise ValueError(f"measured.{name} must be finite{where}")
    if record.measured["cooking_loss_pct"] < 0:
        raise ValueError(f"measured.cooking_loss_pct must be non-negative{where}")
    if "cooking_time_min" not in record.process:
        raise ValueError(f"process.cooking_time_min is required{where}")
    if float(record.process["cooking_time_min"]) <= 0:
        raise ValueError(f"process.cooking_time_min must be positive{where}")
    if "water_temp_c" in record.process and float(record.process["water_temp_c"]) <= 0:
        raise ValueError(f"process.water_temp_c must be positive{where}")
    total = sum(record.mapped_formula.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"mapped_formula must sum to 1.0, got {total}{where}")


def validate_literature_dataset(path: Path | str = DEFAULT_PASTA_DATASET) -> dict[str, Any]:
    records = load_literature_records(path)
    metrics = sorted({metric for record in records for metric in record.measured})
    applications = sorted({record.application for record in records})
    sources = sorted({record.source.get("doi") or record.source.get("pmcid") or record.source.get("url") for record in records})
    return {
        "record_count": len(records),
        "applications": applications,
        "metrics": metrics,
        "source_count": len(sources),
        "sources": sources,
    }


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


def _parse_flour_water_ratio(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if ":" in text:
        flour, water = text.split(":", 1)
        flour_value = float(flour.strip())
        if flour_value <= 0:
            raise ValueError(f"Invalid flour_water_ratio: {value}")
        return float(water.strip()) / flour_value
    return float(text)


def _record_cooking_params(record: LiteratureRecord) -> PastaCookingParams:
    return PastaCookingParams(
        water_temp_c=float(record.process.get("water_temp_c", 98.0)),
        cooking_time_min=float(record.process["cooking_time_min"]),
        pasta_thickness_mm=float(record.process.get("pasta_thickness_mm", 2.0)),
        water_to_flour_ratio=_parse_flour_water_ratio(record.process.get("flour_water_ratio")),
        calcium_lactate_m=float(record.process.get("calcium_lactate_m", 0.0)),
        calcium_bath_time_min=float(record.process.get("calcium_bath_time_min", 0.0)),
        dough_heat_temp_c=float(record.process.get("dough_heat_temp_c", 0.0)),
        dough_heat_time_min=float(record.process.get("dough_heat_time_min", 0.0)),
        dried_pasta=bool(record.process.get("dried_pasta", False)),
        extrusion_moisture_pct=(
            float(record.process["extrusion_moisture_pct"])
            if "extrusion_moisture_pct" in record.process
            else None
        ),
    )


def _round_or_none(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def _source_label(record: LiteratureRecord) -> str:
    return str(
        record.source.get("doi")
        or record.source.get("pmcid")
        or record.source.get("url")
        or record.source.get("title")
        or "unknown"
    )


def _process_family(record: LiteratureRecord) -> str:
    if record.process.get("dried_pasta"):
        return "dried_extruded"
    if (
        float(record.process.get("calcium_lactate_m", 0.0)) > 0
        or float(record.process.get("calcium_bath_time_min", 0.0)) > 0
    ):
        return "fresh_calcium_gel"
    if record.process.get("flour_water_ratio") is not None:
        return "fresh_hydrated"
    return "unknown"


def _group_error_summary(raw_rows: list[tuple[LiteratureRecord, float, float, Any]]) -> dict[str, Any]:
    group_specs = {
        "source": _source_label,
        "process_family": _process_family,
        "flour_water_ratio": lambda record: str(record.process.get("flour_water_ratio", "unknown")),
        "cooking_time_min": lambda record: str(record.process.get("cooking_time_min", "unknown")),
        "alginate_pct": lambda record: str(round(record.mapped_formula.get("Sodium alginate", 0.0) * 100.0, 3)),
    }
    grouped = {}
    for group_name, key_fn in group_specs.items():
        grouped[group_name] = {}
        keys = sorted({key_fn(record) for record, _, _, _ in raw_rows})
        for key in keys:
            measured = [measured_loss for record, measured_loss, _, _ in raw_rows if key_fn(record) == key]
            predicted = [simulated_loss for record, _, simulated_loss, _ in raw_rows if key_fn(record) == key]
            grouped[group_name][key] = _metrics(measured, predicted)
    return grouped


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


def _record_counts(records: list[LiteratureRecord], key_fn) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        key = key_fn(record)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def compare_pasta_cooking_records(
    db: Session,
    records: list[LiteratureRecord] | None = None,
) -> dict[str, Any]:
    records = records or load_literature_records()
    calc = BlendCalculator()
    measured = []
    predicted = []
    metric_values: dict[str, dict[str, list[float]]] = {
        "cooking_loss_pct": {"measured": measured, "predicted": predicted},
        "water_absorption_pct": {"measured": [], "predicted": []},
        "swelling_index": {"measured": [], "predicted": []},
    }
    raw_rows = []

    for record in records:
        blend_data = _blend_data_from_record(record, db)
        props = calc.calculate(blend_data)
        result = PastaCookingSimulator(_record_cooking_params(record)).simulate(props)
        measured_loss = float(record.measured["cooking_loss_pct"])
        measured.append(measured_loss)
        predicted.append(result.cooking_loss_pct)
        if "water_absorption_pct" in record.measured:
            metric_values["water_absorption_pct"]["measured"].append(float(record.measured["water_absorption_pct"]))
            metric_values["water_absorption_pct"]["predicted"].append(result.water_uptake_pct)
        if "swelling_index" in record.measured:
            metric_values["swelling_index"]["measured"].append(float(record.measured["swelling_index"]))
            metric_values["swelling_index"]["predicted"].append(result.swelling_index)
        raw_rows.append((record, measured_loss, result.cooking_loss_pct, result))

    alpha, beta = _fit_linear_correction(predicted, measured)
    corrected = [alpha + beta * value for value in predicted]
    rows = []
    for (record, measured_loss, simulated_loss, result), corrected_loss in zip(raw_rows, corrected):
        rows.append(PastaCalibrationRow(
            id=record.id,
            measured_cooking_loss_pct=round(measured_loss, 4),
            simulated_cooking_loss_pct=round(simulated_loss, 4),
            corrected_cooking_loss_pct=round(corrected_loss, 4),
            residual_before=round(simulated_loss - measured_loss, 4),
            residual_after=round(corrected_loss - measured_loss, 4),
            cooking_time_min=float(record.process["cooking_time_min"]),
            water_to_flour_ratio=_parse_flour_water_ratio(record.process.get("flour_water_ratio")),
            process_family=_process_family(record),
            formula=record.mapped_formula,
            source_doi=record.source.get("doi"),
            source_label=_source_label(record),
            measured_water_absorption_pct=_round_or_none(record.measured.get("water_absorption_pct")),
            simulated_water_absorption_pct=_round_or_none(result.water_uptake_pct),
            measured_swelling_index=_round_or_none(record.measured.get("swelling_index")),
            simulated_swelling_index=_round_or_none(result.swelling_index),
            gelation_index=result.gelation_index,
            pregelatinization_index=result.pregelatinization_index,
            syneresis_index=result.syneresis_index,
            starch_leaching_index=result.starch_leaching_index,
        ))

    metric_summaries = {
        metric: _metrics(values["measured"], values["predicted"])
        for metric, values in metric_values.items()
        if values["measured"]
    }

    return {
        "n_records": len(records),
        "metric": "cooking_loss_pct",
        "source_count": len({record.source.get("doi") for record in records}),
        "correction": {"alpha": round(alpha, 6), "beta": round(beta, 6)},
        "before": _metrics(measured, predicted),
        "after": _metrics(measured, corrected),
        "metric_summaries": metric_summaries,
        "grouped_errors": _group_error_summary(raw_rows),
        "record_groups": {
            "source": _record_counts(records, _source_label),
            "process_family": _record_counts(records, _process_family),
        },
        "rows": [row.__dict__ for row in rows],
        "limitations": [
            "Dataset currently contains cooking-loss rows from two papers.",
            "Lux et al. uses calcium-mediated alginate gelation; the simulator now has a simplified gelation term, not a validated gel-network model.",
            "Liu et al. uses dried twin-screw extruded rice pasta; the simulator now has a simplified dried-extruded branch, not a general extrusion model.",
            "Amaranth flour parameters are approximate literature averages.",
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
        "## Metric Summary",
        "",
        "| Metric | MAE | RMSE | Bias |",
        "|---|---:|---:|---:|",
    ]
    for metric, values in result.get("metric_summaries", {}).items():
        lines.append(f"| {metric} | {values['mae']} | {values['rmse']} | {values['bias']} |")
    lines.extend([
        "",
        "## Record Groups",
        "",
    ])
    for group_name, counts in result.get("record_groups", {}).items():
        lines.extend([
            f"### {group_name}",
            "",
            "| Group | Records |",
            "|---|---:|",
        ])
        for group, count in counts.items():
            lines.append(f"| {group} | {count} |")
        lines.append("")
    lines.extend([
        "## Grouped Raw Error",
        "",
    ])
    for group_name, groups in result.get("grouped_errors", {}).items():
        lines.extend([
            f"### {group_name}",
            "",
            "| Group | MAE | RMSE | Bias |",
            "|---|---:|---:|---:|",
        ])
        for group, values in groups.items():
            lines.append(f"| {group} | {values['mae']} | {values['rmse']} | {values['bias']} |")
        lines.append("")
    lines.extend([
        "## Linear Correction",
        "",
        "```text",
        f"corrected = {result['correction']['alpha']} + {result['correction']['beta']} * simulated",
        "```",
        "",
        "## Rows",
        "",
        "| ID | Time min | W:F | Measured | Simulated | Corrected | Residual Before | Gelation | Pregel | Syneresis |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in result["rows"]:
        lines.append(
            f"| {row['id']} | {row['cooking_time_min']} | {row.get('water_to_flour_ratio')} | "
            f"{row['measured_cooking_loss_pct']} | {row['simulated_cooking_loss_pct']} | "
            f"{row['corrected_cooking_loss_pct']} | {row['residual_before']} | "
            f"{row.get('gelation_index')} | {row.get('pregelatinization_index')} | {row.get('syneresis_index')} |"
        )
    lines.extend([
        "",
        "## Limitations",
        "",
    ])
    lines.extend(f"- {item}" for item in result["limitations"])
    lines.append("")
    return "\n".join(lines)
