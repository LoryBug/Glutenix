"""Small command-line tools for Glutenix experimentation."""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import math
import random
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from glutenix.api.routers.optimization import (
    ApplicationSuggestRequest,
    ApplicationSuggestResponse,
    ProcessRange as ApplicationProcessRange,
    SuggestIngredient,
    suggest_for_application,
)
from glutenix.api.routers.internal import (
    CompareItemRequest,
    CompareWeights,
    ProcessRangeRequest as InternalProcessRange,
    SensitivityPerturbationRequest,
    SensitivityRequest,
    run_sensitivity_analysis,
)
from glutenix.analysis.cohort import CohortFilters, analyze_candidate_cohort
from glutenix.analysis.flavor import explain_flavor
from glutenix.analysis.report import candidate_dossier_markdown, candidate_protocol_markdown
from glutenix.calibration.coverage import assess_literature_coverage, build_domain_coverage
from glutenix.db.base import Base, SessionLocal
from glutenix.db.models import Application, Ingredient, SimulationCandidate, SimulationRun
from glutenix.db.seed import _seed_applications, _seed_ingredients
from glutenix.engine.blend import BlendCalculator, BlendProperties
from glutenix.engine.bread import BreadQualityParams, BreadQualityResult, BreadQualitySimulator
from glutenix.engine.confidence import assess_candidate_confidence, serialize_candidate_confidence
from glutenix.engine.flavor import calculate_blend_flavor, get_flavor_target, score_flavor_against_target
from glutenix.engine.targets import get_sweep_target_profile, score_blend_against_profile


@dataclass(frozen=True)
class IngredientBound:
    name: str
    min_proportion: float
    max_proportion: float


@dataclass(frozen=True)
class ProcessBounds:
    fermentation_temp_c: tuple[float, float] = (30.0, 34.0)
    fermentation_duration_min: tuple[float, float] = (120.0, 180.0)
    baking_temp_c: tuple[float, float] = (200.0, 218.0)
    baking_duration_min: tuple[float, float] = (30.0, 42.0)


@dataclass(frozen=True)
class PaneRankCandidate:
    rank: int
    score: float
    process_score: float
    blend_score: float
    flavor_score: float
    proportions: dict[str, float]
    process: dict[str, float]
    properties: dict[str, float]
    bread_metrics: dict[str, Any]
    model_confidence: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "score": self.score,
            "process_score": self.process_score,
            "blend_score": self.blend_score,
            "flavor_score": self.flavor_score,
            "proportions": self.proportions,
            "process": self.process,
            "properties": self.properties,
            "bread_metrics": self.bread_metrics,
            "model_confidence": self.model_confidence,
        }


PRESETS: dict[str, list[IngredientBound]] = {
    "sorghum-baseline": [
        IngredientBound("Sorghum flour", 0.30, 0.45),
        IngredientBound("White rice flour", 0.20, 0.42),
        IngredientBound("Tapioca starch", 0.18, 0.34),
        IngredientBound("Psyllium husk", 0.012, 0.028),
        IngredientBound("HPMC (Hydroxypropyl Methylcellulose)", 0.012, 0.028),
    ],
    "bobs-inspired": [
        IngredientBound("Sorghum flour", 0.25, 0.45),
        IngredientBound("Potato starch", 0.15, 0.35),
        IngredientBound("Corn starch", 0.10, 0.25),
        IngredientBound("Pea protein powder", 0.03, 0.08),
        IngredientBound("Tapioca starch", 0.10, 0.25),
        IngredientBound("Xanthan gum", 0.005, 0.015),
        IngredientBound("Guar gum", 0.005, 0.015),
    ],
    "schaer-inspired": [
        IngredientBound("Corn starch", 0.35, 0.55),
        IngredientBound("White rice flour", 0.30, 0.50),
        IngredientBound("Brown rice flour", 0.03, 0.08),
        IngredientBound("Chickpea flour", 0.02, 0.06),
        IngredientBound("Psyllium husk", 0.010, 0.030),
        IngredientBound("HPMC (Hydroxypropyl Methylcellulose)", 0.005, 0.020),
    ],
    "freee-inspired": [
        IngredientBound("White rice flour", 0.35, 0.65),
        IngredientBound("Tapioca starch", 0.15, 0.35),
        IngredientBound("Potato starch", 0.15, 0.35),
        IngredientBound("Xanthan gum", 0.005, 0.020),
    ],
    "quinoa-hpmc": [
        IngredientBound("Quinoa flour", 0.20, 0.45),
        IngredientBound("White rice flour", 0.25, 0.55),
        IngredientBound("Tapioca starch", 0.15, 0.35),
        IngredientBound("HPMC (Hydroxypropyl Methylcellulose)", 0.010, 0.030),
    ],
}


def rank_pane_candidates(
    *,
    preset: str,
    n_blend_samples: int = 100,
    n_process_samples: int = 20,
    top: int = 10,
    seed: int | None = None,
    process_bounds: ProcessBounds = ProcessBounds(),
    db: Session | None = None,
) -> list[PaneRankCandidate]:
    if preset not in PRESETS:
        raise ValueError(f"Unknown Pane preset: {preset}")
    if n_blend_samples < 1 or n_process_samples < 1 or top < 1:
        raise ValueError("n_blend_samples, n_process_samples, and top must be positive")

    own_session = db is None
    session = db or _seeded_session()
    try:
        return _rank_pane_candidates(
            session=session,
            bounds=PRESETS[preset],
            n_blend_samples=n_blend_samples,
            n_process_samples=n_process_samples,
            top=top,
            seed=seed,
            process_bounds=process_bounds,
        )
    finally:
        if own_session:
            session.close()


def rank_application_candidates(
    *,
    application: str,
    bounds: list[IngredientBound],
    n_blend_samples: int = 100,
    n_process_samples: int = 20,
    top: int = 10,
    seed: int | None = None,
    process_bounds: ProcessBounds = ProcessBounds(),
    w_process: float = 0.55,
    w_blend: float = 0.25,
    w_flavor: float = 0.20,
    db: Session | None = None,
) -> ApplicationSuggestResponse:
    if n_blend_samples < 1 or n_process_samples < 1 or top < 1:
        raise ValueError("n_blend_samples, n_process_samples, and top must be positive")
    if w_process < 0 or w_blend < 0 or w_flavor < 0:
        raise ValueError("score weights must be non-negative")
    if w_process + w_blend + w_flavor <= 0:
        raise ValueError("at least one score weight must be positive")

    own_session = db is None
    session = db or _seeded_session()
    try:
        application_row = _resolve_application(session, application)
        ingredients = _resolve_ingredients(session, bounds)
        request = ApplicationSuggestRequest(
            application_id=application_row.id,
            ingredients=[
                SuggestIngredient(
                    ingredient_id=ingredient.id,
                    min_proportion=min_proportion,
                    max_proportion=max_proportion,
                )
                for ingredient, min_proportion, max_proportion in ingredients
            ],
            n_candidates=top,
            n_blend_samples=n_blend_samples,
            n_process_samples=n_process_samples,
            seed=seed,
            fermentation_temp=ApplicationProcessRange(
                min=process_bounds.fermentation_temp_c[0],
                max=process_bounds.fermentation_temp_c[1],
            ),
            fermentation_duration=ApplicationProcessRange(
                min=process_bounds.fermentation_duration_min[0],
                max=process_bounds.fermentation_duration_min[1],
            ),
            baking_temp=ApplicationProcessRange(
                min=process_bounds.baking_temp_c[0],
                max=process_bounds.baking_temp_c[1],
            ),
            baking_duration=ApplicationProcessRange(
                min=process_bounds.baking_duration_min[0],
                max=process_bounds.baking_duration_min[1],
            ),
            w_process=w_process,
            w_blend=w_blend,
            w_flavor=w_flavor,
        )
        return suggest_for_application(request, db=session)
    finally:
        if own_session:
            session.close()


def save_pane_run(
    *,
    db: Session,
    preset: str,
    seed: int | None,
    n_blend_samples: int,
    n_process_samples: int,
    top: int,
    candidates: list[PaneRankCandidate],
    notes: str | None = None,
    process_bounds: ProcessBounds = ProcessBounds(),
    git_commit: str | None = None,
) -> SimulationRun:
    application = db.query(Application).filter(Application.name == "Pane").first()
    run = SimulationRun(
        application_id=application.id if application else None,
        application_name="Pane",
        source="cli.rank-pane",
        preset=preset,
        seed=seed,
        blend_samples=n_blend_samples,
        process_samples=n_process_samples,
        top_n=top,
        process_bounds=json.dumps(_process_bounds_dict(process_bounds), sort_keys=True),
        parameters=json.dumps({
            "preset": preset,
            "seed": seed,
            "blend_samples": n_blend_samples,
            "process_samples": n_process_samples,
            "top": top,
        }, sort_keys=True),
        git_commit=git_commit or _current_git_commit(),
        notes=notes,
    )
    db.add(run)
    db.flush()
    for candidate in candidates:
        db.add(SimulationCandidate(
            run_id=run.id,
            rank=candidate.rank,
            score=candidate.score,
            process_score=candidate.process_score,
            blend_score=candidate.blend_score,
            flavor_score=candidate.flavor_score,
            proportions=json.dumps(candidate.proportions, sort_keys=True),
            process=json.dumps(candidate.process, sort_keys=True),
            properties=json.dumps(candidate.properties, sort_keys=True),
            metrics=json.dumps(candidate.bread_metrics, sort_keys=True),
            confidence=json.dumps(candidate.model_confidence, sort_keys=True),
            risk_flags=json.dumps(candidate.model_confidence.get("risk_flags", [])),
        ))
    db.commit()
    db.refresh(run)
    return run


def save_application_run(
    *,
    db: Session,
    result: ApplicationSuggestResponse,
    preset: str,
    seed: int | None,
    n_blend_samples: int,
    n_process_samples: int,
    top: int,
    notes: str | None = None,
    process_bounds: ProcessBounds = ProcessBounds(),
    weights: dict[str, float] | None = None,
    git_commit: str | None = None,
) -> SimulationRun:
    application = db.query(Application).filter(Application.name == result.application).first()
    parameters = {
        "application": result.application,
        "preset": preset,
        "seed": seed,
        "blend_samples": n_blend_samples,
        "process_samples": n_process_samples,
        "top": top,
        "target_profile": result.target_profile,
        "flavor_target": result.flavor_target,
        "weights": weights or {"process": 0.55, "blend": 0.25, "flavor": 0.20},
    }
    run = SimulationRun(
        application_id=application.id if application else None,
        application_name=result.application,
        source="cli.rank-application",
        preset=preset,
        seed=seed,
        blend_samples=n_blend_samples,
        process_samples=n_process_samples,
        top_n=top,
        process_bounds=json.dumps(_process_bounds_dict(process_bounds), sort_keys=True),
        parameters=json.dumps(parameters, sort_keys=True),
        git_commit=git_commit or _current_git_commit(),
        notes=notes,
    )
    db.add(run)
    db.flush()
    for candidate in result.candidates:
        data = candidate.model_dump()
        metrics = data.get("bread_metrics") or data.get("cooking_metrics") or {
            "volume_increase_pct": data.get("volume_increase_pct"),
            "core_temp_c": data.get("core_temp_c"),
            "crust_temp_c": data.get("crust_temp_c"),
        }
        db.add(SimulationCandidate(
            run_id=run.id,
            rank=data["rank"],
            score=data["score"],
            process_score=data["process_score"],
            blend_score=data["blend_score"],
            flavor_score=data["flavor_score"],
            proportions=json.dumps(data["proportions"], sort_keys=True),
            process=json.dumps(data["process"], sort_keys=True),
            properties=json.dumps(data["properties"], sort_keys=True),
            metrics=json.dumps(metrics, sort_keys=True),
            confidence=json.dumps(data["model_confidence"], sort_keys=True),
            risk_flags=json.dumps(data["model_confidence"].get("risk_flags", [])),
        ))
    db.commit()
    db.refresh(run)
    return run


def list_saved_runs(db: Session, limit: int = 20) -> list[SimulationRun]:
    return (
        db.query(SimulationRun)
        .order_by(SimulationRun.created_at.desc(), SimulationRun.id.desc())
        .limit(limit)
        .all()
    )


def mark_candidate(
    *,
    db: Session,
    candidate_id: int,
    status: str,
    notes: str | None = None,
) -> SimulationCandidate:
    candidate = db.get(SimulationCandidate, candidate_id)
    if candidate is None:
        raise ValueError(f"Simulation candidate not found: {candidate_id}")
    candidate.status = status
    if notes is not None:
        candidate.decision_notes = notes
    db.commit()
    db.refresh(candidate)
    return candidate


def _rank_pane_candidates(
    *,
    session: Session,
    bounds: list[IngredientBound],
    n_blend_samples: int,
    n_process_samples: int,
    top: int,
    seed: int | None,
    process_bounds: ProcessBounds,
) -> list[PaneRankCandidate]:
    ingredients = _resolve_ingredients(session, bounds)
    rng = random.Random(seed)
    process_points = _sample_process_points(process_bounds, n_process_samples, rng)
    profile = get_sweep_target_profile("Pane")
    flavor_target = get_flavor_target("Pane")
    coverage_summary = build_domain_coverage(session, "bread_baking")
    calc = BlendCalculator()

    candidates = []
    attempts = 0
    while len(candidates) < n_blend_samples and attempts < n_blend_samples * 20:
        attempts += 1
        proportions = _sample_bounded_proportions(ingredients, rng, max_attempts=20)
        if proportions is None:
            break

        blend_data = [(ingredient, prop) for (ingredient, _, _), prop in zip(ingredients, proportions)]
        blend_props = calc.calculate(blend_data)
        best_bread, best_point, process_score = _best_bread_process(blend_props, process_points, profile)
        blend_values = _blend_values(blend_props)
        blend_score = score_blend_against_profile(blend_values, profile)
        flavor_profile = calculate_blend_flavor(blend_data)
        flavor_score = score_flavor_against_target(flavor_profile, flavor_target)
        total_score = 0.55 * process_score + 0.25 * blend_score + 0.20 * flavor_score
        bread_metrics = _serialize_bread_metrics(best_bread)
        literature_coverage = assess_literature_coverage(
            application="Pane",
            ingredient_names=[ingredient.name for ingredient, prop in blend_data if prop > 1e-6],
            blend_values=blend_values,
            process_values=best_point,
            summary=coverage_summary,
        ).as_dict()
        confidence = serialize_candidate_confidence(assess_candidate_confidence(
            blend_values=blend_values,
            profile=profile,
            process_score=process_score,
            blend_score=blend_score,
            flavor_score=flavor_score,
            bread_metrics=bread_metrics,
            literature_coverage=literature_coverage,
        ))
        candidates.append((
            total_score,
            process_score,
            blend_score,
            flavor_score,
            {ingredient.name: prop for (ingredient, _, _), prop in zip(ingredients, proportions)},
            best_point,
            blend_values,
            bread_metrics,
            confidence,
        ))

    candidates.sort(key=lambda item: item[0], reverse=True)
    return [
        PaneRankCandidate(
            rank=rank,
            score=round(total_score, 4),
            process_score=round(process_score, 4),
            blend_score=round(blend_score, 4),
            flavor_score=round(flavor_score, 4),
            proportions={name: round(value, 4) for name, value in proportions.items()},
            process={key: round(value, 4) for key, value in process.items()},
            properties={key: round(value, 4) for key, value in properties.items()},
            bread_metrics=bread_metrics,
            model_confidence=confidence,
        )
        for rank, (
            total_score,
            process_score,
            blend_score,
            flavor_score,
            proportions,
            process,
            properties,
            bread_metrics,
            confidence,
        ) in enumerate(candidates[:top], start=1)
    ]


def _seeded_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session = Session(bind=engine.connect())
    with contextlib.redirect_stdout(io.StringIO()):
        _seed_ingredients(session)
        _seed_applications(session)
    session.commit()
    return session


def _persistent_session() -> Session:
    session = SessionLocal()
    Base.metadata.create_all(session.get_bind())
    with contextlib.redirect_stdout(io.StringIO()):
        _seed_ingredients(session)
        _seed_applications(session)
    session.commit()
    return session


def _current_git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _process_bounds_dict(bounds: ProcessBounds) -> dict[str, dict[str, float]]:
    return {
        "fermentation_temp_c": {"min": bounds.fermentation_temp_c[0], "max": bounds.fermentation_temp_c[1]},
        "fermentation_duration_min": {
            "min": bounds.fermentation_duration_min[0],
            "max": bounds.fermentation_duration_min[1],
        },
        "baking_temp_c": {"min": bounds.baking_temp_c[0], "max": bounds.baking_temp_c[1]},
        "baking_duration_min": {"min": bounds.baking_duration_min[0], "max": bounds.baking_duration_min[1]},
    }


def _resolve_ingredients(
    session: Session,
    bounds: list[IngredientBound],
) -> list[tuple[Ingredient, float, float]]:
    by_name = {ingredient.name: ingredient for ingredient in session.query(Ingredient).all()}
    items = []
    for bound in bounds:
        ingredient = by_name.get(bound.name)
        if ingredient is None:
            raise ValueError(f"Ingredient not found in seed data: {bound.name}")
        if bound.min_proportion < 0 or bound.max_proportion < bound.min_proportion:
            raise ValueError(f"Invalid proportion bounds for {bound.name}")
        items.append((ingredient, bound.min_proportion, bound.max_proportion))
    return items


def _resolve_application(session: Session, application: str) -> Application:
    row = session.query(Application).filter(Application.name == application).first()
    if row is None:
        available = ", ".join(app.name for app in session.query(Application).order_by(Application.name).all())
        raise ValueError(f"Application not found: {application}. Available: {available}")
    return row


def _parse_ingredient_bound(value: str) -> IngredientBound:
    try:
        name, min_value, max_value = value.rsplit(":", 2)
        min_proportion = float(min_value)
        max_proportion = float(max_value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "ingredient bounds must use 'Ingredient name:min:max', for example 'Sorghum flour:0.25:0.45'"
        ) from exc
    if not name.strip():
        raise argparse.ArgumentTypeError("ingredient name cannot be empty")
    if min_proportion < 0 or max_proportion > 1 or min_proportion > max_proportion:
        raise argparse.ArgumentTypeError("ingredient min/max must satisfy 0 <= min <= max <= 1")
    return IngredientBound(name.strip(), min_proportion, max_proportion)


def _parse_named_proportion(value: str) -> tuple[str, float]:
    try:
        name, proportion_value = value.rsplit(":", 1)
        proportion = float(proportion_value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "ingredient proportions must use 'Ingredient name:proportion', for example 'Sorghum flour:0.40'"
        ) from exc
    if not name.strip():
        raise argparse.ArgumentTypeError("ingredient name cannot be empty")
    if proportion <= 0 or proportion > 1:
        raise argparse.ArgumentTypeError("ingredient proportion must satisfy 0 < proportion <= 1")
    return name.strip(), proportion


def _parse_perturbation(value: str) -> SensitivityPerturbationRequest:
    try:
        name, delta_value = value.rsplit(":", 1)
        delta = float(delta_value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "perturbations must use 'Ingredient name:delta', for example 'Pea protein powder:0.02'"
        ) from exc
    if not name.strip():
        raise argparse.ArgumentTypeError("perturbation ingredient cannot be empty")
    try:
        return SensitivityPerturbationRequest(ingredient=name.strip(), delta=delta)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _sample_bounded_proportions(
    items: list[tuple[Ingredient, float, float]],
    rng: random.Random,
    max_attempts: int,
) -> list[float] | None:
    min_sum = sum(lo for _, lo, _ in items)
    max_sum = sum(hi for _, _, hi in items)
    if min_sum > 1.0 or max_sum < 1.0:
        return None

    for _ in range(max_attempts):
        props = [lo for _, lo, _ in items]
        caps = [hi - lo for _, lo, hi in items]
        remaining = 1.0 - min_sum
        order = list(range(len(items)))
        rng.shuffle(order)

        for pos, idx in enumerate(order[:-1]):
            rest = order[pos + 1:]
            rest_capacity = sum(caps[j] for j in rest)
            min_add = max(0.0, remaining - rest_capacity)
            max_add = min(caps[idx], remaining)
            if min_add > max_add + 1e-12:
                break
            add = rng.uniform(min_add, max_add)
            props[idx] += add
            remaining -= add
        else:
            last = order[-1]
            if remaining <= caps[last] + 1e-9:
                props[last] += remaining
                return props
    return None


def _sample_process_points(
    bounds: ProcessBounds,
    n_samples: int,
    rng: random.Random,
) -> list[dict[str, float]]:
    return [
        {
            "fermentation_temp_c": rng.uniform(*bounds.fermentation_temp_c),
            "fermentation_duration_min": rng.uniform(*bounds.fermentation_duration_min),
            "baking_temp_c": rng.uniform(*bounds.baking_temp_c),
            "baking_duration_min": rng.uniform(*bounds.baking_duration_min),
        }
        for _ in range(n_samples)
    ]


def _best_bread_process(
    blend_props: BlendProperties,
    process_points: list[dict[str, float]],
    profile,
) -> tuple[BreadQualityResult, dict[str, float], float]:
    best_bread = None
    best_point = None
    best_score = -1.0
    for point in process_points:
        bread = BreadQualitySimulator(BreadQualityParams(
            fermentation_temp_c=point["fermentation_temp_c"],
            fermentation_time_min=point["fermentation_duration_min"],
            baking_temp_c=point["baking_temp_c"],
            baking_time_min=point["baking_duration_min"],
        )).simulate(blend_props)
        score = _score_bread_quality(bread, profile)
        if best_bread is None or score > best_score:
            best_bread = bread
            best_point = point
            best_score = score
    if best_bread is None or best_point is None:
        raise ValueError("No process points were generated")
    return best_bread, best_point, best_score


def _score_bread_quality(result: BreadQualityResult, profile) -> float:
    volume_score = math.exp(-0.5 * ((result.specific_volume_cm3_g - 2.5) / 0.6) ** 2)
    core_target = profile.core_target_c or 96.0
    core_score = math.exp(-0.5 * ((result.core_temp_c - core_target) / profile.core_sigma_c) ** 2)
    crust_score = math.exp(-0.5 * ((result.crust_temp_c - profile.crust_target_c) / profile.crust_sigma_c) ** 2)
    return float(0.45 * volume_score + 0.35 * core_score + 0.20 * crust_score)


def _blend_values(props: BlendProperties) -> dict[str, float]:
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


def _serialize_bread_metrics(result: BreadQualityResult) -> dict[str, Any]:
    return {
        "specific_volume_cm3_g": result.specific_volume_cm3_g,
        "crumb_hardness_n": result.crumb_hardness_n,
        "porosity_pct": result.porosity_pct,
        "process_family": result.process_family,
        "calibration_confidence": result.calibration_confidence,
        "calibration_score": result.calibration_score,
        "calibration_notes": result.calibration_notes,
    }


def _print_candidates(candidates: list[PaneRankCandidate]) -> None:
    print("rank score conf vol_cm3_g hard_N protein viscosity top_risk")
    for candidate in candidates:
        confidence = candidate.model_confidence
        bread = candidate.bread_metrics
        properties = candidate.properties
        risks = confidence.get("risk_flags", [])
        top_risk = risks[0] if risks else "none"
        print(
            f"{candidate.rank:>4} "
            f"{candidate.score:>5.3f} "
            f"{confidence['level']:<6} "
            f"{bread['specific_volume_cm3_g']:>8.3f} "
            f"{bread['crumb_hardness_n']:>6.2f} "
            f"{properties['protein_pct']:>7.2f} "
            f"{properties['viscosity_index']:>9.3f} "
            f"{top_risk}"
        )


def _write_json(path: Path, candidates: list[PaneRankCandidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([candidate.as_dict() for candidate in candidates], indent=2),
        encoding="utf-8",
    )


def _write_application_json(path: Path, result: ApplicationSuggestResponse) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.model_dump(), indent=2), encoding="utf-8")


def _write_csv(path: Path, candidates: list[PaneRankCandidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "rank",
            "score",
            "confidence_level",
            "confidence_score",
            "specific_volume_cm3_g",
            "crumb_hardness_n",
            "porosity_pct",
            "protein_pct",
            "viscosity_index",
            "hydrocolloid_pct",
            "fermentation_temp_c",
            "fermentation_duration_min",
            "baking_temp_c",
            "baking_duration_min",
            "proportions_json",
            "top_risk",
        ])
        writer.writeheader()
        for candidate in candidates:
            risks = candidate.model_confidence.get("risk_flags", [])
            writer.writerow({
                "rank": candidate.rank,
                "score": candidate.score,
                "confidence_level": candidate.model_confidence["level"],
                "confidence_score": candidate.model_confidence["score"],
                "specific_volume_cm3_g": candidate.bread_metrics["specific_volume_cm3_g"],
                "crumb_hardness_n": candidate.bread_metrics["crumb_hardness_n"],
                "porosity_pct": candidate.bread_metrics["porosity_pct"],
                "protein_pct": candidate.properties["protein_pct"],
                "viscosity_index": candidate.properties["viscosity_index"],
                "hydrocolloid_pct": candidate.properties["hydrocolloid_pct"],
                "fermentation_temp_c": candidate.process["fermentation_temp_c"],
                "fermentation_duration_min": candidate.process["fermentation_duration_min"],
                "baking_temp_c": candidate.process["baking_temp_c"],
                "baking_duration_min": candidate.process["baking_duration_min"],
                "proportions_json": json.dumps(candidate.proportions, sort_keys=True),
                "top_risk": risks[0] if risks else "",
            })


def _print_application_candidates(result: ApplicationSuggestResponse) -> None:
    print(f"application={result.application} target={result.target_profile} flavor={result.flavor_target}")
    print("rank score conf process blend flavor protein viscosity primary_metric top_risk")
    for candidate in result.candidates:
        data = candidate.model_dump()
        confidence = data["model_confidence"]
        properties = data["properties"]
        risks = confidence.get("risk_flags", [])
        print(
            f"{data['rank']:>4} "
            f"{data['score']:>5.3f} "
            f"{confidence['level']:<6} "
            f"{data['process_score']:>7.3f} "
            f"{data['blend_score']:>5.3f} "
            f"{data['flavor_score']:>6.3f} "
            f"{properties['protein_pct']:>7.2f} "
            f"{properties['viscosity_index']:>9.3f} "
            f"{_primary_metric(data):<22} "
            f"{risks[0] if risks else 'none'}"
        )


def _primary_metric(candidate: dict[str, Any]) -> str:
    bread = candidate.get("bread_metrics")
    if bread:
        return f"vol={bread['specific_volume_cm3_g']:.3f} hard={bread['crumb_hardness_n']:.2f}"
    cooking = candidate.get("cooking_metrics")
    if cooking:
        return f"loss={cooking['cooking_loss_pct']:.2f} firm={cooking['firmness_index']:.2f}"
    return f"vol_pct={candidate.get('volume_increase_pct', 0):.2f}"


def _rank_pane_command(args: argparse.Namespace) -> int:
    session = _persistent_session() if args.save_run else None
    try:
        candidates = rank_pane_candidates(
            preset=args.preset,
            n_blend_samples=args.blend_samples,
            n_process_samples=args.process_samples,
            top=args.top,
            seed=args.seed,
            db=session,
        )
        _print_candidates(candidates)
        if args.json:
            _write_json(Path(args.json), candidates)
            print(f"JSON written to {args.json}")
        if args.csv:
            _write_csv(Path(args.csv), candidates)
            print(f"CSV written to {args.csv}")
        if args.save_run:
            assert session is not None
            run = save_pane_run(
                db=session,
                preset=args.preset,
                seed=args.seed,
                n_blend_samples=args.blend_samples,
                n_process_samples=args.process_samples,
                top=args.top,
                candidates=candidates,
                notes=args.notes,
            )
            print(f"Saved run #{run.id} with {len(run.candidates)} candidates")
    finally:
        if session is not None:
            session.close()
    return 0


def _rank_application_command(args: argparse.Namespace) -> int:
    custom_bounds = [_parse_ingredient_bound(value) for value in args.ingredient]
    if custom_bounds:
        bounds = custom_bounds
        preset = "custom"
    else:
        bounds = PRESETS[args.preset]
        preset = args.preset
    process_bounds = ProcessBounds(
        fermentation_temp_c=tuple(args.fermentation_temp),
        fermentation_duration_min=tuple(args.fermentation_duration),
        baking_temp_c=tuple(args.baking_temp),
        baking_duration_min=tuple(args.baking_duration),
    )
    session = _persistent_session() if args.save_run else None
    try:
        result = rank_application_candidates(
            application=args.application,
            bounds=bounds,
            n_blend_samples=args.blend_samples,
            n_process_samples=args.process_samples,
            top=args.top,
            seed=args.seed,
            process_bounds=process_bounds,
            w_process=args.w_process,
            w_blend=args.w_blend,
            w_flavor=args.w_flavor,
            db=session,
        )
        _print_application_candidates(result)
        if args.json:
            _write_application_json(Path(args.json), result)
            print(f"JSON written to {args.json}")
        if args.save_run:
            assert session is not None
            run = save_application_run(
                db=session,
                result=result,
                preset=preset,
                seed=args.seed,
                n_blend_samples=args.blend_samples,
                n_process_samples=args.process_samples,
                top=args.top,
                notes=args.notes,
                process_bounds=process_bounds,
                weights={"process": args.w_process, "blend": args.w_blend, "flavor": args.w_flavor},
            )
            print(f"Saved run #{run.id} with {len(run.candidates)} candidates")
    finally:
        if session is not None:
            session.close()
    return 0


def _runs_list_command(args: argparse.Namespace) -> int:
    session = _persistent_session()
    try:
        runs = list_saved_runs(session, limit=args.limit)
        print("id created_at application preset status candidates top_score notes")
        for run in runs:
            top_score = run.candidates[0].score if run.candidates else 0.0
            created = _format_datetime(run.created_at)
            notes = (run.notes or "").replace("\n", " ")[:40]
            print(
                f"{run.id:<4} {created:<19} {run.application_name:<11} "
                f"{run.preset or '-':<17} {run.status:<8} {len(run.candidates):<10} "
                f"{top_score:<8.4f} {notes}"
            )
    finally:
        session.close()
    return 0


def _runs_show_command(args: argparse.Namespace) -> int:
    session = _persistent_session()
    try:
        run = session.get(SimulationRun, args.run_id)
        if run is None:
            raise SystemExit(f"Run not found: {args.run_id}")
        print(f"Run #{run.id} {run.application_name} preset={run.preset} status={run.status}")
        print(f"created_at={_format_datetime(run.created_at)} seed={run.seed} samples={run.blend_samples}x{run.process_samples} top={run.top_n}")
        print(f"git_commit={run.git_commit or '-'} notes={run.notes or ''}")
        print("candidate_id rank status score conf process blend flavor protein viscosity primary_metric top_risk")
        for candidate in run.candidates:
            metrics = json.loads(candidate.metrics)
            properties = json.loads(candidate.properties)
            confidence = json.loads(candidate.confidence)
            risks = json.loads(candidate.risk_flags or "[]")
            top_risk = risks[0] if risks else "none"
            print(
                f"{candidate.id:<12} {candidate.rank:<4} {candidate.status:<9} "
                f"{candidate.score:<5.3f} {confidence['level']:<6} "
                f"{candidate.process_score:<7.3f} "
                f"{candidate.blend_score:<5.3f} "
                f"{candidate.flavor_score:<6.3f} "
                f"{properties['protein_pct']:<7.2f} "
                f"{properties['viscosity_index']:<9.3f} "
                f"{_saved_primary_metric(metrics):<22} {top_risk}"
            )
    finally:
        session.close()
    return 0


def _candidate_mark_command(args: argparse.Namespace) -> int:
    session = _persistent_session()
    try:
        candidate = mark_candidate(
            db=session,
            candidate_id=args.candidate_id,
            status=args.status,
            notes=args.notes,
        )
        print(f"Candidate #{candidate.id} marked {candidate.status}")
    finally:
        session.close()
    return 0


def _candidate_report_command(args: argparse.Namespace) -> int:
    session = _persistent_session()
    try:
        try:
            markdown = candidate_dossier_markdown(session, args.candidate_id)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        if args.markdown:
            path = Path(args.markdown)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(markdown, encoding="utf-8")
            print(f"Markdown written to {args.markdown}")
        else:
            print(markdown)
    finally:
        session.close()
    return 0


def _candidate_protocol_command(args: argparse.Namespace) -> int:
    session = _persistent_session()
    try:
        try:
            markdown = candidate_protocol_markdown(session, args.candidate_id, args.batch_g)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        if args.markdown:
            path = Path(args.markdown)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(markdown, encoding="utf-8")
            print(f"Markdown written to {args.markdown}")
        else:
            print(markdown)
    finally:
        session.close()
    return 0


def _cohort_analyze_command(args: argparse.Namespace) -> int:
    session = _persistent_session()
    try:
        result = analyze_candidate_cohort(session, CohortFilters(
            application=args.application,
            preset=args.preset,
            statuses=tuple(args.status or ()),
            run_ids=tuple(args.run_id or ()),
            max_rank=args.max_rank,
            limit=args.limit,
        ))
        _print_cohort_analysis(result)
        if args.json:
            path = Path(args.json)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(f"JSON written to {args.json}")
    finally:
        session.close()
    return 0


def _sensitivity_analyze_command(args: argparse.Namespace) -> int:
    sources = [args.candidate_id is not None, args.blend_id is not None, bool(args.ingredient)]
    if sum(sources) != 1:
        raise SystemExit("Provide exactly one of --candidate-id, --blend-id, or repeated --ingredient.")
    proportions = dict(args.ingredient or []) or None
    process_bounds = ProcessBounds(
        fermentation_temp_c=tuple(args.fermentation_temp),
        fermentation_duration_min=tuple(args.fermentation_duration),
        baking_temp_c=tuple(args.baking_temp),
        baking_duration_min=tuple(args.baking_duration),
    )
    request = SensitivityRequest(
        application=args.application,
        base=CompareItemRequest(
            candidate_id=args.candidate_id,
            blend_id=args.blend_id,
            proportions=proportions,
        ),
        perturbations=args.perturb,
        compensate_with=args.compensate_with,
        n_process_samples=args.process_samples,
        seed=args.seed,
        fermentation_temp=InternalProcessRange(
            min=process_bounds.fermentation_temp_c[0],
            max=process_bounds.fermentation_temp_c[1],
        ),
        fermentation_duration=InternalProcessRange(
            min=process_bounds.fermentation_duration_min[0],
            max=process_bounds.fermentation_duration_min[1],
        ),
        baking_temp=InternalProcessRange(
            min=process_bounds.baking_temp_c[0],
            max=process_bounds.baking_temp_c[1],
        ),
        baking_duration=InternalProcessRange(
            min=process_bounds.baking_duration_min[0],
            max=process_bounds.baking_duration_min[1],
        ),
        weights=CompareWeights(process=args.w_process, blend=args.w_blend, flavor=args.w_flavor),
    )
    session = _persistent_session()
    try:
        result = run_sensitivity_analysis(session, request).model_dump()
        _print_sensitivity_analysis(result)
        if args.json:
            path = Path(args.json)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(f"JSON written to {args.json}")
    finally:
        session.close()
    return 0


def _flavor_explain_command(args: argparse.Namespace) -> int:
    sources = [args.candidate_id is not None, args.blend_id is not None, bool(args.ingredient)]
    if sum(sources) != 1:
        raise SystemExit("Provide exactly one of --candidate-id, --blend-id, or repeated --ingredient.")
    proportions = dict(args.ingredient or []) or None
    session = _persistent_session()
    try:
        result = explain_flavor(
            session,
            application=args.application,
            candidate_id=args.candidate_id,
            blend_id=args.blend_id,
            proportions=proportions,
        )
        _print_flavor_explanation(result)
        if args.json:
            path = Path(args.json)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(f"JSON written to {args.json}")
    finally:
        session.close()
    return 0


def _format_datetime(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _print_cohort_analysis(result: dict[str, Any]) -> None:
    print(
        f"candidates={result['candidate_count']} runs={result['run_count']} "
        f"statuses={result['status_counts']} presets={result['preset_counts']}"
    )
    print("\nTop candidates")
    print("candidate_id run_id rank status preset score")
    for candidate in result["top_candidates"][:10]:
        print(
            f"{candidate['candidate_id']:<12} {candidate['run_id']:<6} {candidate['rank']:<4} "
            f"{candidate['status']:<9} {candidate['preset'] or '-':<17} {candidate['score']:<6.4f}"
        )

    print("\nIngredient ranges (% dry blend)")
    print("ingredient count min mean max")
    for name, summary in result["ingredients"].items():
        print(
            f"{name:<38} {summary['count']:<5} {summary['min']:<7.2f} "
            f"{summary['mean']:<7.2f} {summary['max']:<7.2f}"
        )

    print("\nKey metric ranges")
    print("metric count min mean max")
    for name in (
        "score",
        "specific_volume_cm3_g",
        "crumb_hardness_n",
        "protein_pct",
        "viscosity_index",
        "hydrocolloid_pct",
        "flavor_score",
    ):
        summary = result["metrics"].get(name)
        if summary:
            print(
                f"{name:<24} {summary['count']:<5} {summary['min']:<8.4f} "
                f"{summary['mean']:<8.4f} {summary['max']:<8.4f}"
            )


def _print_sensitivity_analysis(result: dict[str, Any]) -> None:
    base = result["base"]
    print(
        f"application={result['application']} target={result['target_profile']} "
        f"base_score={base['score']:.4f}"
    )
    print("variant score d_score d_process d_blend d_flavor d_protein d_viscosity d_volume d_hardness")
    for variant in result["variants"]:
        deltas = variant["deltas"]
        row = variant["result"]
        print(
            f"{variant['name']:<32} "
            f"{row['score']:<6.4f} "
            f"{deltas.get('score', 0):<7.4f} "
            f"{deltas.get('process_score', 0):<9.4f} "
            f"{deltas.get('blend_score', 0):<7.4f} "
            f"{deltas.get('flavor_score', 0):<8.4f} "
            f"{deltas.get('properties.protein_pct', 0):<9.4f} "
            f"{deltas.get('properties.viscosity_index', 0):<11.4f} "
            f"{deltas.get('bread_metrics.specific_volume_cm3_g', 0):<8.4f} "
            f"{deltas.get('bread_metrics.crumb_hardness_n', 0):<8.4f}"
        )


def _print_flavor_explanation(result: dict[str, Any]) -> None:
    print(
        f"application={result['application']} target={result['target']['name']} "
        f"flavor_score={result['flavor_score']:.4f}"
    )
    print("\nInterpretation")
    for item in result["interpretation"]:
        print(f"- {item}")
    print("\nFlavor profile vs target")
    print("dimension profile target gap")
    for dim, value in result["profile"].items():
        target = result["target"]["profile"][dim]
        gap = result["gaps_vs_target"][dim]
        print(f"{dim:<10} {value:<7.3f} {target:<7.3f} {gap:<+7.3f}")
    print("\nTop ingredient contributions")
    print("ingredient proportion dominant effect risk")
    for row in result["contributions"][:8]:
        dominant = ",".join(row["dominant_dimensions"])
        print(f"{row['ingredient']:<32} {row['proportion']:<10.4f} {dominant:<22} {row['effect']} | {row['risk']}")


def _saved_primary_metric(metrics: dict[str, Any]) -> str:
    if "specific_volume_cm3_g" in metrics:
        return f"vol={metrics['specific_volume_cm3_g']:.3f} hard={metrics['crumb_hardness_n']:.2f}"
    if "cooking_loss_pct" in metrics:
        return f"loss={metrics['cooking_loss_pct']:.2f} firm={metrics['firmness_index']:.2f}"
    if "volume_increase_pct" in metrics:
        return f"vol_pct={metrics['volume_increase_pct']:.2f}"
    return "-"


def _add_process_bound_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--fermentation-temp", nargs=2, type=float, default=(30.0, 34.0), metavar=("MIN", "MAX"))
    parser.add_argument("--fermentation-duration", nargs=2, type=float, default=(120.0, 180.0), metavar=("MIN", "MAX"))
    parser.add_argument("--baking-temp", nargs=2, type=float, default=(200.0, 218.0), metavar=("MIN", "MAX"))
    parser.add_argument("--baking-duration", nargs=2, type=float, default=(30.0, 42.0), metavar=("MIN", "MAX"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    rank_pane = subparsers.add_parser(
        "rank-pane",
        help="Rank Pane blend candidates without starting the API.",
    )
    rank_pane.add_argument("--preset", choices=sorted(PRESETS), default="sorghum-baseline")
    rank_pane.add_argument("--blend-samples", type=int, default=100)
    rank_pane.add_argument("--process-samples", type=int, default=20)
    rank_pane.add_argument("--top", type=int, default=10)
    rank_pane.add_argument("--seed", type=int, default=None)
    rank_pane.add_argument("--json", help="Optional JSON output path.")
    rank_pane.add_argument("--csv", help="Optional CSV output path.")
    rank_pane.add_argument("--save-run", action="store_true", help="Persist this run and its top candidates.")
    rank_pane.add_argument("--notes", help="Optional notes stored with --save-run.")
    rank_pane.set_defaults(func=_rank_pane_command)

    rank_application = subparsers.add_parser(
        "rank-application",
        help="Rank application-specific blend candidates using process, blend, flavor, and confidence engines.",
    )
    rank_application.add_argument("--application", default="Pane", help="Application name, for example Pane or Pasta fresca.")
    rank_application.add_argument("--preset", choices=sorted(PRESETS), default="bobs-inspired")
    rank_application.add_argument(
        "--ingredient",
        action="append",
        default=[],
        help="Custom ingredient bound as 'Ingredient name:min:max'. Repeat to override --preset.",
    )
    rank_application.add_argument("--blend-samples", type=int, default=100)
    rank_application.add_argument("--process-samples", type=int, default=20)
    rank_application.add_argument("--top", type=int, default=10)
    rank_application.add_argument("--seed", type=int, default=None)
    rank_application.add_argument("--w-process", type=float, default=0.55)
    rank_application.add_argument("--w-blend", type=float, default=0.25)
    rank_application.add_argument("--w-flavor", type=float, default=0.20)
    _add_process_bound_args(rank_application)
    rank_application.add_argument("--json", help="Optional JSON output path.")
    rank_application.add_argument("--save-run", action="store_true", help="Persist this run and its top candidates.")
    rank_application.add_argument("--notes", help="Optional notes stored with --save-run.")
    rank_application.set_defaults(func=_rank_application_command)

    runs = subparsers.add_parser("runs", help="Inspect saved simulation runs.")
    runs_subparsers = runs.add_subparsers(dest="runs_command", required=True)
    runs_list = runs_subparsers.add_parser("list", help="List saved simulation runs.")
    runs_list.add_argument("--limit", type=int, default=20)
    runs_list.set_defaults(func=_runs_list_command)
    runs_show = runs_subparsers.add_parser("show", help="Show a saved simulation run.")
    runs_show.add_argument("run_id", type=int)
    runs_show.set_defaults(func=_runs_show_command)

    candidates = subparsers.add_parser("candidates", help="Annotate saved simulation candidates.")
    candidates_subparsers = candidates.add_subparsers(dest="candidates_command", required=True)
    candidate_mark = candidates_subparsers.add_parser("mark", help="Update candidate decision status.")
    candidate_mark.add_argument("candidate_id", type=int)
    candidate_mark.add_argument(
        "--status",
        required=True,
        choices=["new", "promising", "avoid", "test_next", "tested", "archived"],
    )
    candidate_mark.add_argument("--notes", help="Decision notes for this candidate.")
    candidate_mark.set_defaults(func=_candidate_mark_command)
    candidate_report = candidates_subparsers.add_parser("report", help="Generate a Markdown dossier for a saved candidate.")
    candidate_report.add_argument("candidate_id", type=int)
    candidate_report.add_argument("--markdown", help="Optional Markdown output path. Prints to stdout when omitted.")
    candidate_report.set_defaults(func=_candidate_report_command)
    candidate_protocol = candidates_subparsers.add_parser(
        "protocol",
        help="Generate a Markdown physical-test protocol for a saved candidate.",
    )
    candidate_protocol.add_argument("candidate_id", type=int)
    candidate_protocol.add_argument("--batch-g", type=float, default=500.0, help="Dry blend batch size in grams.")
    candidate_protocol.add_argument("--markdown", help="Optional Markdown output path. Prints to stdout when omitted.")
    candidate_protocol.set_defaults(func=_candidate_protocol_command)

    cohort = subparsers.add_parser("cohort", help="Analyze saved simulation candidate cohorts.")
    cohort_subparsers = cohort.add_subparsers(dest="cohort_command", required=True)
    cohort_analyze = cohort_subparsers.add_parser("analyze", help="Summarize candidate ingredient and metric ranges.")
    cohort_analyze.add_argument("--application", help="Filter by application name, for example Pane.")
    cohort_analyze.add_argument("--preset", help="Filter by saved run preset.")
    cohort_analyze.add_argument(
        "--status",
        action="append",
        choices=["new", "promising", "avoid", "test_next", "tested", "archived"],
        help="Filter by candidate status. Repeat for multiple statuses.",
    )
    cohort_analyze.add_argument("--run-id", action="append", type=int, help="Filter by run id. Repeat for multiple runs.")
    cohort_analyze.add_argument("--max-rank", type=int, help="Only include candidates with rank <= this value.")
    cohort_analyze.add_argument("--limit", type=int, help="Limit candidates after sorting by score.")
    cohort_analyze.add_argument("--json", help="Optional JSON output path.")
    cohort_analyze.set_defaults(func=_cohort_analyze_command)

    sensitivity = subparsers.add_parser("sensitivity", help="Analyze local ingredient perturbations.")
    sensitivity_subparsers = sensitivity.add_subparsers(dest="sensitivity_command", required=True)
    sensitivity_analyze = sensitivity_subparsers.add_parser("analyze", help="Compare perturbations against a base formula.")
    sensitivity_analyze.add_argument("--application", default="Pane", help="Application name, for example Pane.")
    sensitivity_analyze.add_argument("--candidate-id", type=int, help="Use a saved simulation candidate as the base formula.")
    sensitivity_analyze.add_argument("--blend-id", type=int, help="Use a saved blend as the base formula.")
    sensitivity_analyze.add_argument(
        "--ingredient",
        action="append",
        type=_parse_named_proportion,
        help="Custom base ingredient as 'Ingredient name:proportion'. Repeat for custom formulas.",
    )
    sensitivity_analyze.add_argument(
        "--perturb",
        action="append",
        type=_parse_perturbation,
        required=True,
        help="Perturbation as 'Ingredient name:delta'. Repeat for multiple variants.",
    )
    sensitivity_analyze.add_argument("--compensate-with", required=True, help="Ingredient adjusted by -delta.")
    sensitivity_analyze.add_argument("--process-samples", type=int, default=40)
    sensitivity_analyze.add_argument("--seed", type=int, default=None)
    sensitivity_analyze.add_argument("--w-process", type=float, default=0.55)
    sensitivity_analyze.add_argument("--w-blend", type=float, default=0.25)
    sensitivity_analyze.add_argument("--w-flavor", type=float, default=0.20)
    _add_process_bound_args(sensitivity_analyze)
    sensitivity_analyze.add_argument("--json", help="Optional JSON output path.")
    sensitivity_analyze.set_defaults(func=_sensitivity_analyze_command)

    flavor = subparsers.add_parser("flavor", help="Explain flavor score and ingredient contributions.")
    flavor_subparsers = flavor.add_subparsers(dest="flavor_command", required=True)
    flavor_explain = flavor_subparsers.add_parser("explain", help="Explain a candidate, blend, or custom formula flavor score.")
    flavor_explain.add_argument("--application", default="Pane", help="Application name, for example Pane.")
    flavor_explain.add_argument("--candidate-id", type=int, help="Use a saved simulation candidate as the formula.")
    flavor_explain.add_argument("--blend-id", type=int, help="Use a saved blend as the formula.")
    flavor_explain.add_argument(
        "--ingredient",
        action="append",
        type=_parse_named_proportion,
        help="Custom ingredient as 'Ingredient name:proportion'. Repeat for custom formulas.",
    )
    flavor_explain.add_argument("--json", help="Optional JSON output path.")
    flavor_explain.set_defaults(func=_flavor_explain_command)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
