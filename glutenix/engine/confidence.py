from dataclasses import dataclass
from enum import Enum
from typing import Any

from glutenix.engine.targets import SweepTargetProfile


class ConfidenceTier(str, Enum):
    CALIBRATED = "calibrated"
    LITERATURE_INFORMED = "literature_informed"
    HEURISTIC = "heuristic"
    OOD_EXTRAPOLATION = "ood_extrapolation"


@dataclass(frozen=True)
class RiskWarning:
    tier: ConfidenceTier
    description: str
    affected_variables: list[str]
    severity: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier.value,
            "description": self.description,
            "affected_variables": self.affected_variables,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class CandidateConfidence:
    score: float
    level: str
    basis: list[str]
    risk_flags: list[str]
    confidence_summary: ConfidenceTier
    risk_warnings: list[RiskWarning]


def assess_candidate_confidence(
    *,
    blend_values: dict[str, float],
    profile: SweepTargetProfile,
    process_score: float,
    blend_score: float,
    flavor_score: float,
    cooking_metrics: dict | None = None,
    bread_metrics: dict | None = None,
    literature_coverage: dict[str, Any] | None = None,
) -> CandidateConfidence:
    basis: list[str] = []
    risk_flags: list[str] = []
    risk_warnings: list[RiskWarning] = []

    range_score = _range_coverage(blend_values, profile, basis, risk_flags, risk_warnings)
    process_confidence = _score_band(process_score, "process", basis, risk_flags, risk_warnings)
    blend_confidence = _score_band(blend_score, "blend target", basis, risk_flags, risk_warnings)
    flavor_confidence = _score_band(flavor_score, "flavor", basis, risk_flags, risk_warnings)

    if cooking_metrics is not None:
        calibration_score = float(cooking_metrics.get("calibration_score", 0.25))
        cooking_confidence = max(0.0, min(calibration_score, 1.0))
        confidence = cooking_metrics.get("calibration_confidence", "unknown")
        basis.append(f"Pasta cooking model calibration confidence: {confidence}.")
        if confidence in {"high", "medium"}:
            basis.append("Pasta cooking outputs are calibrated against structured literature records for covered process families.")
        else:
            risk_warnings.append(_warning(
                ConfidenceTier.HEURISTIC,
                f"Pasta cooking calibration confidence is {confidence}; treat uncovered metrics as heuristic.",
                ["cooking_metrics"],
                "medium",
            ))
    elif bread_metrics is not None:
        calibration_score = float(bread_metrics.get("calibration_score", 0.25))
        cooking_confidence = max(0.0, min(calibration_score, 1.0))
        confidence = bread_metrics.get("calibration_confidence", "unknown")
        family = bread_metrics.get("process_family", "unknown")
        basis.append(f"Bread quality model calibration confidence: {confidence} ({family}).")
        bread_flags = [str(item) for item in bread_metrics.get("calibration_notes", [])]
        risk_flags.extend(bread_flags)
        for flag in bread_flags:
            risk_warnings.append(_warning(
                ConfidenceTier.HEURISTIC if confidence == "low" else ConfidenceTier.LITERATURE_INFORMED,
                flag,
                _affected_variables(flag),
                "medium" if confidence != "low" else "high",
            ))
        if confidence in {"high", "medium"}:
            basis.append("Bread quality outputs are literature-informed and diagnostically compared where matching bread records exist.")
        else:
            risk_warnings.append(_warning(
                ConfidenceTier.HEURISTIC,
                f"Bread quality calibration confidence is {confidence}; treat bread metrics as heuristic outside covered families.",
                ["bread_metrics", "process_family"],
                "medium",
            ))
    else:
        cooking_confidence = 0.45
        risk_flags.append("No direct experimental calibration attached to this application model yet.")
        risk_warnings.append(_warning(
            ConfidenceTier.HEURISTIC,
            "No direct experimental calibration is attached to this application model yet.",
            ["application"],
            "medium",
        ))

    literature_level = None
    literature_mechanism = 1.0
    literature_calibration = 1.0
    if literature_coverage is not None:
        literature_confidence = max(0.0, min(float(literature_coverage.get("score", 0.25)), 1.0))
        literature_level = str(literature_coverage.get("level", "unknown"))
        literature_mechanism = float(literature_coverage.get("mechanism_coverage", 1.0))
        literature_calibration = float(literature_coverage.get("calibration_coverage", 1.0))
        basis.append(f"Literature coverage/OOD confidence: {literature_level}.")
        basis.append(
            "Literature coverage components: "
            f"range={literature_confidence:.2f}, "
            f"mechanism={literature_mechanism:.2f}, "
            f"calibration={literature_calibration:.2f}."
        )
        basis.extend(str(item) for item in literature_coverage.get("basis", []))
        literature_flags = [str(item) for item in literature_coverage.get("risk_flags", [])]
        risk_flags.extend(literature_flags)
        for flag in literature_flags:
            risk_warnings.append(_warning(
                ConfidenceTier.OOD_EXTRAPOLATION,
                flag,
                _affected_variables(flag),
                _severity_for_ood(flag, literature_level, literature_mechanism, literature_calibration),
            ))
    else:
        literature_confidence = None

    if literature_confidence is None:
        score = (
            0.25 * range_score
            + 0.20 * process_confidence
            + 0.20 * blend_confidence
            + 0.15 * flavor_confidence
            + 0.20 * cooking_confidence
        )
    else:
        score = (
            0.20 * range_score
            + 0.17 * process_confidence
            + 0.17 * blend_confidence
            + 0.13 * flavor_confidence
            + 0.18 * cooking_confidence
            + 0.15 * literature_confidence
        )
    score = round(max(0.0, min(score, 1.0)), 4)

    if literature_level == "low" or literature_mechanism < 0.5 or literature_calibration < 0.5:
        level = "low"
    elif score >= 0.75 and len(risk_flags) <= 2:
        level = "high"
    elif score >= 0.50:
        level = "medium"
    else:
        level = "low"

    if not basis:
        basis.append("Candidate uses fallback heuristic coverage only.")

    confidence_summary = _confidence_summary(
        level=level,
        literature_level=literature_level,
        literature_mechanism=literature_mechanism,
        literature_calibration=literature_calibration,
        cooking_metrics=cooking_metrics,
        bread_metrics=bread_metrics,
        risk_warnings=risk_warnings,
    )

    return CandidateConfidence(
        score=score,
        level=level,
        basis=basis,
        risk_flags=risk_flags,
        confidence_summary=confidence_summary,
        risk_warnings=risk_warnings,
    )


def serialize_candidate_confidence(confidence: CandidateConfidence) -> dict:
    return {
        "score": confidence.score,
        "level": confidence.level,
        "basis": confidence.basis,
        "risk_flags": confidence.risk_flags,
        "confidence_summary": confidence.confidence_summary.value,
        "risk_warnings": [warning.as_dict() for warning in confidence.risk_warnings],
    }


def _range_coverage(
    values: dict[str, float],
    profile: SweepTargetProfile,
    basis: list[str],
    risk_flags: list[str],
    risk_warnings: list[RiskWarning],
) -> float:
    if not profile.blend_ranges:
        description = "No blend-property target ranges are defined for this application."
        risk_flags.append(description)
        risk_warnings.append(_warning(ConfidenceTier.HEURISTIC, description, ["blend_ranges"], "medium"))
        return 0.45

    weighted = 0.0
    total_weight = 0.0
    inside_count = 0
    checked_count = 0
    for metric, (min_value, max_value, weight) in profile.blend_ranges.items():
        if metric not in values:
            continue
        value = values[metric]
        checked_count += 1
        total_weight += weight
        width = max(max_value - min_value, 1e-6)
        if min_value <= value <= max_value:
            metric_score = 1.0
            inside_count += 1
        else:
            distance = min(abs(value - min_value), abs(value - max_value))
            metric_score = max(0.0, 1.0 - distance / width)
            direction = "below" if value < min_value else "above"
            description = (
                f"{metric} is {direction} target range "
                f"({value:.4g}; expected {min_value:.4g}-{max_value:.4g})."
            )
            risk_flags.append(description)
            severity = "high" if metric_score < 0.35 else "medium"
            risk_warnings.append(_warning(ConfidenceTier.OOD_EXTRAPOLATION, description, [metric], severity))
        weighted += weight * metric_score

    if total_weight <= 0:
        description = "Blend-property range coverage could not be evaluated."
        risk_flags.append(description)
        risk_warnings.append(_warning(ConfidenceTier.HEURISTIC, description, ["blend_properties"], "medium"))
        return 0.45

    if inside_count == checked_count:
        basis.append("All evaluated blend properties are inside the target profile ranges.")
    elif inside_count >= max(1, checked_count - 1):
        basis.append("Most blend properties are inside the target profile ranges.")
    else:
        description = "Several blend properties are outside the target profile ranges."
        risk_flags.append(description)
        risk_warnings.append(_warning(ConfidenceTier.OOD_EXTRAPOLATION, description, ["blend_properties"], "high"))

    return weighted / total_weight


def _score_band(
    score: float,
    label: str,
    basis: list[str],
    risk_flags: list[str],
    risk_warnings: list[RiskWarning],
) -> float:
    score = max(0.0, min(float(score), 1.0))
    if score >= 0.75:
        basis.append(f"{label.capitalize()} score is strong.")
    elif score < 0.45:
        description = f"{label.capitalize()} score is weak."
        risk_flags.append(description)
        risk_warnings.append(_warning(ConfidenceTier.HEURISTIC, description, [label.replace(" ", "_")], "medium"))
    return score


def _warning(
    tier: ConfidenceTier,
    description: str,
    affected_variables: list[str],
    severity: str,
) -> RiskWarning:
    return RiskWarning(
        tier=tier,
        description=description,
        affected_variables=sorted({item for item in affected_variables if item}),
        severity=severity,
    )


def _affected_variables(description: str) -> list[str]:
    known = [
        "application",
        "ingredient",
        "water_absorption",
        "viscosity_index",
        "hydrocolloid_pct",
        "protein_pct",
        "starch_pct",
        "fat_pct",
        "fiber_pct",
        "amylose_pct",
        "hydration_pct",
        "baking_temp_c",
        "baking_time_min",
        "fermentation_temp_c",
        "fermentation_time_min",
        "water_temp_c",
        "cooking_time_min",
        "water_to_flour_ratio",
        "tg_pct",
    ]
    affected = [key for key in known if key in description]
    if "Ingredients outside" in description:
        affected.append("ingredients")
    return affected or ["candidate"]


def _severity_for_ood(
    description: str,
    literature_level: str | None,
    mechanism_coverage: float,
    calibration_coverage: float,
) -> str:
    if literature_level == "low" or mechanism_coverage < 0.5 or calibration_coverage < 0.5:
        return "high"
    if "outside" in description.lower() or "ood" in description.lower():
        return "medium"
    return "low"


def _confidence_summary(
    *,
    level: str,
    literature_level: str | None,
    literature_mechanism: float,
    literature_calibration: float,
    cooking_metrics: dict | None,
    bread_metrics: dict | None,
    risk_warnings: list[RiskWarning],
) -> ConfidenceTier:
    if any(warning.tier == ConfidenceTier.OOD_EXTRAPOLATION for warning in risk_warnings):
        return ConfidenceTier.OOD_EXTRAPOLATION
    if literature_level == "low" or literature_mechanism < 0.5 or literature_calibration < 0.5:
        return ConfidenceTier.OOD_EXTRAPOLATION

    calibration_confidence = None
    if cooking_metrics is not None:
        calibration_confidence = cooking_metrics.get("calibration_confidence")
    elif bread_metrics is not None:
        calibration_confidence = bread_metrics.get("calibration_confidence")

    if calibration_confidence == "high" and level == "high":
        return ConfidenceTier.CALIBRATED
    if calibration_confidence in {"high", "medium"} or literature_level in {"high", "medium"}:
        return ConfidenceTier.LITERATURE_INFORMED
    return ConfidenceTier.HEURISTIC
