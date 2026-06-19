from dataclasses import dataclass

from glutenix.engine.targets import SweepTargetProfile


@dataclass(frozen=True)
class CandidateConfidence:
    score: float
    level: str
    basis: list[str]
    risk_flags: list[str]


def assess_candidate_confidence(
    *,
    blend_values: dict[str, float],
    profile: SweepTargetProfile,
    process_score: float,
    blend_score: float,
    flavor_score: float,
    cooking_metrics: dict | None = None,
) -> CandidateConfidence:
    basis: list[str] = []
    risk_flags: list[str] = []

    range_score = _range_coverage(blend_values, profile, basis, risk_flags)
    process_confidence = _score_band(process_score, "process", basis, risk_flags)
    blend_confidence = _score_band(blend_score, "blend target", basis, risk_flags)
    flavor_confidence = _score_band(flavor_score, "flavor", basis, risk_flags)

    if cooking_metrics is not None:
        calibration_score = float(cooking_metrics.get("calibration_score", 0.25))
        cooking_confidence = max(0.0, min(calibration_score, 1.0))
        confidence = cooking_metrics.get("calibration_confidence", "unknown")
        basis.append(f"Pasta cooking model calibration confidence: {confidence}.")
    else:
        cooking_confidence = 0.45
        risk_flags.append("No direct experimental calibration attached to this application model yet.")

    score = (
        0.25 * range_score
        + 0.20 * process_confidence
        + 0.20 * blend_confidence
        + 0.15 * flavor_confidence
        + 0.20 * cooking_confidence
    )
    score = round(max(0.0, min(score, 1.0)), 4)

    if score >= 0.75 and len(risk_flags) <= 2:
        level = "high"
    elif score >= 0.50:
        level = "medium"
    else:
        level = "low"

    if not basis:
        basis.append("Candidate uses fallback heuristic coverage only.")

    return CandidateConfidence(
        score=score,
        level=level,
        basis=basis,
        risk_flags=risk_flags,
    )


def serialize_candidate_confidence(confidence: CandidateConfidence) -> dict:
    return {
        "score": confidence.score,
        "level": confidence.level,
        "basis": confidence.basis,
        "risk_flags": confidence.risk_flags,
    }


def _range_coverage(
    values: dict[str, float],
    profile: SweepTargetProfile,
    basis: list[str],
    risk_flags: list[str],
) -> float:
    if not profile.blend_ranges:
        risk_flags.append("No blend-property target ranges are defined for this application.")
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
            risk_flags.append(
                f"{metric} is {direction} target range "
                f"({value:.4g}; expected {min_value:.4g}-{max_value:.4g})."
            )
        weighted += weight * metric_score

    if total_weight <= 0:
        risk_flags.append("Blend-property range coverage could not be evaluated.")
        return 0.45

    if inside_count == checked_count:
        basis.append("All evaluated blend properties are inside the target profile ranges.")
    elif inside_count >= max(1, checked_count - 1):
        basis.append("Most blend properties are inside the target profile ranges.")
    else:
        risk_flags.append("Several blend properties are outside the target profile ranges.")

    return weighted / total_weight


def _score_band(score: float, label: str, basis: list[str], risk_flags: list[str]) -> float:
    score = max(0.0, min(float(score), 1.0))
    if score >= 0.75:
        basis.append(f"{label.capitalize()} score is strong.")
    elif score < 0.45:
        risk_flags.append(f"{label.capitalize()} score is weak.")
    return score
