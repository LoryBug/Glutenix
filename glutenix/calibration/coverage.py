from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from glutenix.calibration.literature import (
    DEFAULT_BREAD_DATASET,
    LiteratureRecord,
    _blend_data_from_record,
    _bread_process_family,
    _parse_flour_water_ratio,
    _process_family,
    _record_counts,
    _source_label,
    load_literature_records,
)
from glutenix.engine.blend import BlendCalculator, BlendProperties


@dataclass(frozen=True)
class NumericRange:
    min: float
    max: float

    def as_dict(self) -> dict[str, float]:
        return {"min": round(self.min, 6), "max": round(self.max, 6)}


@dataclass(frozen=True)
class LiteratureCoverageSummary:
    domain: str
    application: str
    record_count: int
    source_count: int
    measured_metrics: list[str]
    covered_ingredients: list[str]
    process_families: dict[str, int]
    process_ranges: dict[str, NumericRange]
    blend_property_ranges: dict[str, NumericRange]
    limitations: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "application": self.application,
            "record_count": self.record_count,
            "source_count": self.source_count,
            "measured_metrics": self.measured_metrics,
            "covered_ingredients": self.covered_ingredients,
            "process_families": self.process_families,
            "process_ranges": {key: value.as_dict() for key, value in self.process_ranges.items()},
            "blend_property_ranges": {key: value.as_dict() for key, value in self.blend_property_ranges.items()},
            "limitations": self.limitations,
        }


@dataclass(frozen=True)
class CoverageAssessment:
    score: float
    level: str
    basis: list[str]
    risk_flags: list[str]
    ingredient_coverage: float
    blend_property_coverage: float
    process_coverage: float
    mechanism_coverage: float = 1.0
    calibration_coverage: float = 1.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "level": self.level,
            "basis": self.basis,
            "risk_flags": self.risk_flags,
            "ingredient_coverage": round(self.ingredient_coverage, 4),
            "blend_property_coverage": round(self.blend_property_coverage, 4),
            "process_coverage": round(self.process_coverage, 4),
            "mechanism_coverage": round(self.mechanism_coverage, 4),
            "calibration_coverage": round(self.calibration_coverage, 4),
        }


def summarize_literature_coverage(db: Session) -> dict[str, Any]:
    pasta = build_domain_coverage(db, "pasta_cooking")
    bread = build_domain_coverage(db, "bread_baking")
    return {
        "domains": {
            "pasta_cooking": pasta.as_dict(),
            "bread_baking": bread.as_dict(),
        },
        "limitations": [
            "Coverage ranges are derived from currently structured JSONL records only.",
            "Inside-range does not mean validated for all interactions; it means the candidate is less extrapolative than outside-range candidates.",
            "Ingredient coverage is name-based and does not yet account for cultivar, supplier, or processing differences.",
        ],
    }


def build_domain_coverage(db: Session, domain: str) -> LiteratureCoverageSummary:
    if domain == "pasta_cooking":
        records = load_literature_records()
        application = "Pasta fresca"
        family_fn = _process_family
        limitations = [
            "Pasta coverage is strongest for calcium-alginate fresh pasta, dried extruded rice pasta, and instant extrusion-cooked rice/rice-buckwheat pasta.",
            "Generic fresh pasta, egg pasta, and legume pasta remain extrapolative unless matched by future records.",
        ]
    elif domain == "bread_baking":
        records = load_literature_records(
            DEFAULT_BREAD_DATASET,
            required_measured_metrics=(),
            required_process_fields=("hydration_pct", "baking_time_min"),
        )
        application = "Pane"
        family_fn = _bread_process_family
        limitations = [
            "Bread coverage is strongest for specific volume and limited for porosity.",
            "Crumb hardness coverage is broader but unreliable for enzyme-treated quinoa/HPMC systems.",
            "Microbial transglutaminase is tracked as a mechanism-OOD process field but is not modeled yet.",
        ]
    else:
        raise ValueError(f"Unknown literature coverage domain: {domain}")

    calc = BlendCalculator()
    blend_values = []
    for record in records:
        props = calc.calculate(_blend_data_from_record(record, db))
        blend_values.append(_blend_property_values(props))

    return LiteratureCoverageSummary(
        domain=domain,
        application=application,
        record_count=len(records),
        source_count=len({_source_label(record) for record in records}),
        measured_metrics=sorted({metric for record in records for metric in record.measured}),
        covered_ingredients=sorted({name for record in records for name in record.mapped_formula}),
        process_families=_record_counts(records, family_fn),
        process_ranges=_process_ranges(records),
        blend_property_ranges=_ranges_from_values(blend_values),
        limitations=limitations,
    )


def assess_application_literature_coverage(
    *,
    application: str,
    ingredient_names: list[str],
    blend_values: dict[str, float],
    process_values: dict[str, float],
    db: Session,
) -> CoverageAssessment:
    domain = domain_for_application(application)
    if domain is None:
        return CoverageAssessment(
            score=0.15,
            level="low",
            basis=[],
            risk_flags=[f"No structured literature coverage is available for application '{application}'."],
            ingredient_coverage=0.0,
            blend_property_coverage=0.0,
            process_coverage=0.0,
            mechanism_coverage=0.0,
            calibration_coverage=0.0,
        )

    summary = build_domain_coverage(db, domain)
    return assess_literature_coverage(
        application=application,
        ingredient_names=ingredient_names,
        blend_values=blend_values,
        process_values=process_values,
        summary=summary,
    )


def assess_literature_coverage(
    *,
    application: str,
    ingredient_names: list[str],
    blend_values: dict[str, float],
    process_values: dict[str, float],
    summary: LiteratureCoverageSummary | None,
) -> CoverageAssessment:
    if summary is None:
        return CoverageAssessment(
            score=0.15,
            level="low",
            basis=[],
            risk_flags=[f"No structured literature coverage is available for application '{application}'."],
            ingredient_coverage=0.0,
            blend_property_coverage=0.0,
            process_coverage=0.0,
            mechanism_coverage=0.0,
            calibration_coverage=0.0,
        )

    basis: list[str] = []
    risk_flags: list[str] = []

    ingredient_score = _ingredient_coverage(ingredient_names, summary.covered_ingredients, basis, risk_flags)
    blend_score = _range_coverage_score(
        values=blend_values,
        ranges=summary.blend_property_ranges,
        label="blend property",
        basis=basis,
        risk_flags=risk_flags,
    )
    process_score = _range_coverage_score(
        values=process_values,
        ranges=summary.process_ranges,
        label="process",
        basis=basis,
        risk_flags=risk_flags,
    )

    mechanism_score, calibration_score = _mechanism_calibration_coverage(
        summary=summary,
        ingredient_names=ingredient_names,
        process_values=process_values,
        basis=basis,
        risk_flags=risk_flags,
    )

    score = round(
        0.25 * ingredient_score
        + 0.25 * blend_score
        + 0.20 * process_score
        + 0.15 * mechanism_score
        + 0.15 * calibration_score,
        4,
    )
    if mechanism_score < 0.5 or calibration_score < 0.5:
        level = "low"
    elif score >= 0.75 and not risk_flags:
        level = "high"
    elif score >= 0.5:
        level = "medium"
    else:
        level = "low"

    if not basis:
        basis.append("Literature coverage could only be evaluated with low confidence.")

    return CoverageAssessment(
        score=score,
        level=level,
        basis=basis,
        risk_flags=risk_flags,
        ingredient_coverage=ingredient_score,
        blend_property_coverage=blend_score,
        process_coverage=process_score,
        mechanism_coverage=mechanism_score,
        calibration_coverage=calibration_score,
    )


def _mechanism_calibration_coverage(
    *,
    summary: LiteratureCoverageSummary,
    ingredient_names: list[str],
    process_values: dict[str, float],
    basis: list[str],
    risk_flags: list[str],
) -> tuple[float, float]:
    if summary.domain != "bread_baking":
        return 1.0, 1.0

    names = " ".join(ingredient_names).lower()
    tg_pct = float(process_values.get("tg_pct", 0.0))
    if tg_pct > 0:
        basis.append("Microbial transglutaminase appears in bread literature coverage, but enzyme effects are not modeled yet.")
        risk_flags.append("tg_pct uses an unmodeled enzyme mechanism; treat bread quality predictions as mechanism-OOD.")
        return 0.0, 0.25

    if "quinoa" in names:
        basis.append("Quinoa bread coverage is currently sparse outside the Ghodosipoor enzyme/HPMC study.")
        risk_flags.append("Quinoa flour has sparse non-enzyme bread calibration; treat predictions as low confidence.")
        return 1.0, 0.35

    if any(token in names for token in ("hpmc", "xanthan", "guar", "psyllium")):
        basis.append("Plain hydrocolloid bread has multiple non-enzyme literature sources, but family-specific errors remain.")
        return 1.0, 0.75

    basis.append("No mechanism-specific bread calibration adjustment was applied.")
    return 1.0, 0.6


def domain_for_application(application: str) -> str | None:
    normalized = application.strip().lower()
    if normalized == "pasta fresca":
        return "pasta_cooking"
    if normalized == "pane":
        return "bread_baking"
    return None


def _blend_property_values(props: BlendProperties) -> dict[str, float]:
    return {
        "protein_pct": props.protein_pct,
        "starch_pct": props.starch_pct,
        "fat_pct": props.fat_pct,
        "fiber_pct": props.fiber_pct,
        "water_absorption": props.water_absorption,
        "viscosity_index": props.viscosity_index,
        "hydrocolloid_pct": props.hydrocolloid_pct,
        "amylose_pct": props.amylose_pct,
    }


def _process_values(record: LiteratureRecord) -> dict[str, float]:
    values: dict[str, float] = {}
    for key, value in record.process.items():
        if isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            values[key] = float(value)
    water_to_flour_ratio = _parse_flour_water_ratio(record.process.get("flour_water_ratio"))
    if water_to_flour_ratio is not None:
        values["water_to_flour_ratio"] = water_to_flour_ratio
    return values


def _process_ranges(records: list[LiteratureRecord]) -> dict[str, NumericRange]:
    return _ranges_from_values([_process_values(record) for record in records])


def _ranges_from_values(rows: list[dict[str, float]]) -> dict[str, NumericRange]:
    keys = sorted({key for row in rows for key in row})
    ranges = {}
    for key in keys:
        values = [row[key] for row in rows if key in row]
        if values:
            ranges[key] = NumericRange(min=min(values), max=max(values))
    return ranges


def _ingredient_coverage(
    ingredient_names: list[str],
    covered_ingredients: list[str],
    basis: list[str],
    risk_flags: list[str],
) -> float:
    names = sorted({name for name in ingredient_names if name})
    if not names:
        risk_flags.append("Candidate ingredient coverage could not be evaluated.")
        return 0.25

    covered = set(covered_ingredients)
    missing = [name for name in names if name not in covered]
    score = (len(names) - len(missing)) / len(names)
    if not missing:
        basis.append("All candidate ingredients appear in the structured literature dataset for this application.")
    else:
        risk_flags.append(f"Ingredients outside structured literature coverage: {', '.join(missing)}.")
    return score


def _range_coverage_score(
    *,
    values: dict[str, float],
    ranges: dict[str, NumericRange],
    label: str,
    basis: list[str],
    risk_flags: list[str],
) -> float:
    checked = 0
    total = 0.0
    inside = 0
    for key, value in values.items():
        if key not in ranges:
            continue
        checked += 1
        range_ = ranges[key]
        width = max(range_.max - range_.min, 1e-6)
        if range_.min <= value <= range_.max:
            total += 1.0
            inside += 1
        else:
            distance = min(abs(value - range_.min), abs(value - range_.max))
            total += max(0.0, 1.0 - distance / width)
            direction = "below" if value < range_.min else "above"
            risk_flags.append(
                f"{label.capitalize()} '{key}' is {direction} literature coverage "
                f"({value:.4g}; observed {range_.min:.4g}-{range_.max:.4g})."
            )

    if checked == 0:
        risk_flags.append(f"No comparable {label} coverage ranges were available.")
        return 0.25
    if inside == checked:
        basis.append(f"All comparable {label} values are inside structured literature coverage ranges.")
    elif inside >= max(1, checked - 1):
        basis.append(f"Most comparable {label} values are inside structured literature coverage ranges.")
    else:
        risk_flags.append(f"Several comparable {label} values are outside structured literature coverage ranges.")
    return total / checked
