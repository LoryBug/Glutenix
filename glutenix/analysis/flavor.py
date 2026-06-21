from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from glutenix.db.models import Blend, Ingredient, SimulationCandidate
from glutenix.engine.flavor import (
    FLAVOR_DIMENSIONS,
    calculate_blend_flavor,
    get_flavor_target,
    get_ingredient_flavor_profile,
    score_flavor_against_target,
    serialize_flavor_target,
)


def explain_flavor(
    db: Session,
    *,
    application: str,
    candidate_id: int | None = None,
    blend_id: int | None = None,
    proportions: dict[str, float] | None = None,
) -> dict[str, Any]:
    sources = [candidate_id is not None, blend_id is not None, proportions is not None]
    if sum(sources) != 1:
        raise ValueError("Provide exactly one of candidate_id, blend_id, or proportions")

    source, blend_data = _resolve_blend_data(db, candidate_id, blend_id, proportions)
    blend_data = _normalize_blend_data(blend_data)
    target = get_flavor_target(application)
    profile = calculate_blend_flavor(blend_data)
    score = score_flavor_against_target(profile, target)
    gaps = {
        dim: round(profile.get(dim, 0.0) - target.profile[dim], 4)
        for dim in FLAVOR_DIMENSIONS
    }
    contributions = _ingredient_contributions(blend_data)
    risk_notes = _risk_notes(blend_data, profile, gaps)
    interpretation = _interpretation(score, gaps, risk_notes, target.name)
    return {
        "application": application,
        "target": serialize_flavor_target(target),
        "source": source,
        "flavor_score": round(score, 4),
        "profile": profile,
        "gaps_vs_target": gaps,
        "contributions": contributions,
        "risk_notes": risk_notes,
        "interpretation": interpretation,
        "evidence_note": "Flavor explanation is heuristic and not calibrated with sensory panel data.",
    }


def _resolve_blend_data(
    db: Session,
    candidate_id: int | None,
    blend_id: int | None,
    proportions: dict[str, float] | None,
) -> tuple[dict[str, Any], list[tuple[Ingredient, float]]]:
    if candidate_id is not None:
        candidate = db.get(SimulationCandidate, candidate_id)
        if candidate is None:
            raise ValueError(f"Simulation candidate not found: {candidate_id}")
        return (
            {"type": "candidate", "id": candidate.id, "run_id": candidate.run_id},
            _blend_data_from_proportions(db, json.loads(candidate.proportions)),
        )
    if blend_id is not None:
        blend = db.get(Blend, blend_id)
        if blend is None:
            raise ValueError(f"Blend not found: {blend_id}")
        return (
            {"type": "blend", "id": blend.id, "name": blend.name},
            [(item.ingredient, item.proportion) for item in blend.ingredients],
        )
    assert proportions is not None
    return ({"type": "custom", "id": "custom"}, _blend_data_from_proportions(db, proportions))


def _blend_data_from_proportions(
    db: Session,
    proportions: dict[str, float],
) -> list[tuple[Ingredient, float]]:
    ingredients = {ingredient.name: ingredient for ingredient in db.query(Ingredient).all()}
    missing = sorted(set(proportions) - set(ingredients))
    if missing:
        raise ValueError(f"Ingredients not found: {missing}")
    return [(ingredients[name], proportion) for name, proportion in proportions.items()]


def _normalize_blend_data(blend_data: list[tuple[Ingredient, float]]) -> list[tuple[Ingredient, float]]:
    total = sum(proportion for _, proportion in blend_data)
    if total <= 0:
        raise ValueError("Blend proportions must sum to a positive value")
    if abs(total - 1.0) > 1e-3:
        raise ValueError(f"Blend proportions must sum to 1.0, got {total}")
    return [(ingredient, proportion / total) for ingredient, proportion in blend_data]


def _ingredient_contributions(blend_data: list[tuple[Ingredient, float]]) -> list[dict[str, Any]]:
    rows = []
    for ingredient, proportion in blend_data:
        profile = get_ingredient_flavor_profile(ingredient)
        weighted = {dim: round(profile[dim] * proportion, 4) for dim in FLAVOR_DIMENSIONS}
        dominant = sorted(FLAVOR_DIMENSIONS, key=lambda dim: weighted[dim], reverse=True)[:3]
        rows.append({
            "ingredient": ingredient.name,
            "proportion": round(proportion, 4),
            "dominant_dimensions": dominant,
            "weighted_profile": weighted,
            "effect": _ingredient_effect(ingredient.name, profile, proportion),
            "risk": _ingredient_risk(ingredient.name, profile, proportion),
        })
    rows.sort(key=lambda row: row["proportion"], reverse=True)
    return rows


def _ingredient_effect(name: str, profile: dict[str, float], proportion: float) -> str:
    if "pea protein" in name.lower():
        return "improves protein but may add legume/beany perception"
    if profile["neutral"] >= 0.85:
        return "mostly dilutes stronger flavor notes and keeps the blend clean"
    top = max(FLAVOR_DIMENSIONS, key=lambda dim: profile[dim] if dim != "neutral" else -1)
    return f"adds {top} character to the blend"


def _ingredient_risk(name: str, profile: dict[str, float], proportion: float) -> str:
    lowered = name.lower()
    if "pea protein" in lowered and proportion >= 0.06:
        return "watch legume/beany perception at this protein level"
    if profile["bitter"] >= 0.20 and proportion >= 0.10:
        return "bitter note may become noticeable"
    if profile["earthy"] >= 0.35 and proportion >= 0.10:
        return "earthy/bran-like note may dominate"
    if profile["neutral"] >= 0.85:
        return "low sensory risk in the current heuristic model"
    return "moderate sensory contribution; confirm with tasting"


def _risk_notes(
    blend_data: list[tuple[Ingredient, float]],
    profile: dict[str, float],
    gaps: dict[str, float],
) -> list[str]:
    notes = []
    if gaps.get("bitter", 0.0) > 0.04:
        notes.append("Blend is more bitter than the target profile.")
    if gaps.get("earthy", 0.0) > 0.08:
        notes.append("Blend is more earthy than the target profile.")
    if gaps.get("cereal", 0.0) < -0.10:
        notes.append("Cereal note is lower than target; product may taste too neutral/starchy.")
    for ingredient, proportion in blend_data:
        if "pea protein" in ingredient.name.lower() and proportion >= 0.06:
            notes.append("Pea protein is near or above a practical sensory watch threshold.")
    return notes or ["No major heuristic flavor risks detected."]


def _interpretation(
    score: float,
    gaps: dict[str, float],
    risk_notes: list[str],
    target_name: str,
) -> list[str]:
    if score >= 0.90:
        first = f"Strong flavor match for {target_name} target."
    elif score >= 0.75:
        first = f"Acceptable flavor match for {target_name}, but sensory checks remain important."
    else:
        first = f"Weak flavor match for {target_name}; reformulation or tasting is recommended."
    largest = max(gaps, key=lambda dim: abs(gaps[dim]))
    direction = "above" if gaps[largest] > 0 else "below"
    return [
        first,
        f"Largest target gap is {largest}, {direction} target by {abs(gaps[largest]):.3f}.",
        risk_notes[0],
    ]
