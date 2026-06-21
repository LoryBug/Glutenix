from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PIZZA_V1_AUDIT_DOC = "docs/pizza-v1-literature-audit.md"

PIZZA_V1_SUPPORTED_INGREDIENTS = {
    "White rice flour",
    "Brown rice flour",
    "Sweet rice flour (Mochiko)",
    "Tapioca starch",
    "Sorghum flour",
    "Corn flour",
    "Corn starch",
    "Xanthan gum",
    "Psyllium husk",
    "HPMC (Hydroxypropyl Methylcellulose)",
}

PIZZA_V1_VARIABLE_RANGES: dict[str, tuple[float, float, str, str]] = {
    "water_absorption": (1.2, 1.9, "heuristic", "Working target range; not a pizza calibration curve."),
    "viscosity_index": (1.4, 2.8, "heuristic", "Working target range; not directly measured in Pizza V1 sources."),
    "hydrocolloid_pct": (0.001, 0.04, "literature_informed", "Bounded by Dey xanthan and Pasqualone psyllium/HPMC anchors."),
    "fiber_pct": (2.0, 8.0, "heuristic", "Working target range; Pasqualone nutrition supports moderate fiber only."),
    "fat_pct": (0.0, 6.0, "heuristic", "Working target range; Dey reports low oil addition."),
    "fermentation_temp_c": (37.0, 37.0, "literature_informed", "Dey GF pizza fermentation anchor."),
    "fermentation_duration_min": (120.0, 120.0, "literature_informed", "Dey GF pizza fermentation anchor."),
    "baking_temp_c": (204.4, 204.4, "literature_informed", "Dey GF pizza baking anchor."),
    "baking_duration_min": (10.0, 10.0, "literature_informed", "Dey GF pizza baking anchor."),
}


@dataclass(frozen=True)
class PizzaV1VariableDiagnostic:
    variable: str
    status: str
    value: float | str | None
    supported_range: dict[str, float] | None
    confidence_tier: str
    evidence_level: str
    source: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "variable": self.variable,
            "status": self.status,
            "value": self.value,
            "supported_range": self.supported_range,
            "confidence_tier": self.confidence_tier,
            "evidence_level": self.evidence_level,
            "source": self.source,
            "message": self.message,
        }


@dataclass(frozen=True)
class PizzaV1CoverageDiagnostics:
    application: str
    preset: str
    audit_doc: str
    coverage_fraction: float
    warning: bool
    variable_diagnostics: list[PizzaV1VariableDiagnostic]
    unsupported_variables: list[str]
    risk_flags: list[str]
    basis: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "application": self.application,
            "preset": self.preset,
            "audit_doc": self.audit_doc,
            "coverage_fraction": self.coverage_fraction,
            "warning": self.warning,
            "variable_diagnostics": [item.as_dict() for item in self.variable_diagnostics],
            "unsupported_variables": self.unsupported_variables,
            "risk_flags": self.risk_flags,
            "basis": self.basis,
        }

    def as_literature_coverage(self) -> dict[str, Any]:
        level = "medium" if self.coverage_fraction >= 0.75 and not self.warning else "low"
        return {
            "score": self.coverage_fraction,
            "level": level,
            "basis": self.basis,
            "risk_flags": self.risk_flags,
            "mechanism_coverage": 0.6 if level == "medium" else 0.35,
            "calibration_coverage": 0.0,
        }


def is_pizza_v1_application(application: str) -> bool:
    return application.strip().lower() == "pizza"


def assess_pizza_v1_coverage(
    *,
    ingredient_names: list[str],
    blend_values: dict[str, float],
    process_values: dict[str, float],
) -> PizzaV1CoverageDiagnostics:
    diagnostics: list[PizzaV1VariableDiagnostic] = []
    risk_flags: list[str] = []
    basis = [
        f"Pizza V1 evidence boundaries are defined in {PIZZA_V1_AUDIT_DOC}.",
        "Pizza V1 is not calibrated because no structured pizza_baking JSONL dataset exists.",
    ]

    for name in sorted({name for name in ingredient_names if name}):
        if name in PIZZA_V1_SUPPORTED_INGREDIENTS:
            diagnostics.append(_ingredient_diag(name, "in_range", "Ingredient family appears in current Pizza V1 audit sources."))
        else:
            message = f"Ingredient '{name}' is outside Pizza V1 audited ingredient families."
            risk_flags.append(message)
            diagnostics.append(_ingredient_diag(name, "unsupported", message))

    for variable, (min_value, max_value, tier, note) in PIZZA_V1_VARIABLE_RANGES.items():
        value = blend_values.get(variable, process_values.get(variable))
        if value is None:
            diagnostics.append(PizzaV1VariableDiagnostic(
                variable=variable,
                status="unsupported",
                value=None,
                supported_range={"min": min_value, "max": max_value},
                confidence_tier=tier,
                evidence_level=_evidence_level(tier),
                source=PIZZA_V1_AUDIT_DOC,
                message=f"{variable} was not available for Pizza V1 coverage assessment.",
            ))
            continue
        tolerance = 0.01 if min_value == max_value else 0.0
        if min_value - tolerance <= float(value) <= max_value + tolerance:
            status = "in_range"
            message = note
        else:
            status = "out_of_range"
            message = f"{variable}={float(value):.4g} is outside Pizza V1 audited range {min_value:.4g}-{max_value:.4g}."
            risk_flags.append(message)
        diagnostics.append(PizzaV1VariableDiagnostic(
            variable=variable,
            status=status,
            value=round(float(value), 6),
            supported_range={"min": min_value, "max": max_value},
            confidence_tier=tier,
            evidence_level=_evidence_level(tier),
            source=PIZZA_V1_AUDIT_DOC,
            message=message,
        ))

    assessed = [item for item in diagnostics if item.status != "unsupported"]
    in_range = [item for item in assessed if item.status == "in_range"]
    coverage_fraction = round(len(in_range) / len(diagnostics), 4) if diagnostics else 0.0
    unsupported = [item.variable for item in diagnostics if item.status in {"out_of_range", "unsupported"}]
    if coverage_fraction < 0.5:
        risk_flags.append("Pizza V1 coverage fraction is below 0.5; treat this candidate as strongly extrapolative.")

    return PizzaV1CoverageDiagnostics(
        application="Pizza",
        preset="pizza-v1",
        audit_doc=PIZZA_V1_AUDIT_DOC,
        coverage_fraction=coverage_fraction,
        warning=bool(risk_flags),
        variable_diagnostics=diagnostics,
        unsupported_variables=unsupported,
        risk_flags=risk_flags,
        basis=basis,
    )


def _ingredient_diag(name: str, status: str, message: str) -> PizzaV1VariableDiagnostic:
    return PizzaV1VariableDiagnostic(
        variable=f"ingredient:{name}",
        status=status,
        value=name,
        supported_range=None,
        confidence_tier="literature_informed" if status == "in_range" else "ood_extrapolation",
        evidence_level="moderate" if status == "in_range" else "weak",
        source=PIZZA_V1_AUDIT_DOC,
        message=message,
    )


def _evidence_level(tier: str) -> str:
    if tier == "literature_informed":
        return "weak-moderate"
    return "weak"
