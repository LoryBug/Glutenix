import math
import random
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from glutenix.api.deps import get_db, get_gpr
from glutenix.bo.explain import ard_feature_importance
from glutenix.calibration.coverage import (
    assess_literature_coverage,
    build_domain_coverage,
    domain_for_application,
)
from glutenix.calibration.pizza_v1 import assess_pizza_v1_coverage, is_pizza_v1_application
from glutenix.db.models import Application, Ingredient
from glutenix.engine.baking import BakingParams, BakingSimulator
from glutenix.engine.blend import BlendCalculator
from glutenix.engine.bread import BreadQualityParams, BreadQualityResult, BreadQualitySimulator
from glutenix.engine.confidence import (
    assess_candidate_confidence,
    serialize_candidate_confidence,
)
from glutenix.engine.cooking import PastaCookingSimulator, pasta_v1_process_params, serialize_pasta_process_params
from glutenix.engine.flavor import (
    APPLICATION_FLAVOR_TARGETS,
    DEFAULT_FLAVOR_TARGET,
    calculate_blend_flavor,
    get_flavor_target,
    score_flavor_against_target,
    serialize_flavor_target,
)
from glutenix.engine.fermentation import FermentationParams, FermentationSimulator
from glutenix.engine.sweep import SimulationSweeper, SweepRange
from glutenix.engine.targets import get_sweep_target_profile, score_blend_against_profile
from glutenix.ml.gpr import PhysicsGPR

router = APIRouter(prefix="/optimize", tags=["optimization"])


class ARDResponse(BaseModel):
    importance: dict[str, float]


@router.get("/ard", response_model=ARDResponse)
def ard(gpr: PhysicsGPR = Depends(get_gpr)):
    if not gpr.is_trained:
        return ARDResponse(importance={name: 1.0 for name in gpr.FEATURE_NAMES})
    imp = ard_feature_importance(gpr)
    return ARDResponse(importance=imp)


class FlavorTargetResponse(BaseModel):
    name: str
    profile: dict[str, float]
    sigma: float
    evidence_level: str
    rationale: str
    sources: list[str]


@router.get("/flavor-targets", response_model=list[FlavorTargetResponse])
def flavor_targets():
    targets = [DEFAULT_FLAVOR_TARGET, *APPLICATION_FLAVOR_TARGETS.values()]
    return [serialize_flavor_target(target) for target in targets]


class SuggestIngredient(BaseModel):
    ingredient_id: int = Field(gt=0)
    min_proportion: float = Field(ge=0, le=1, default=0)
    max_proportion: float = Field(ge=0, le=1, default=1)

    @model_validator(mode="after")
    def min_not_greater_than_max(self):
        if self.min_proportion > self.max_proportion:
            raise ValueError("min_proportion must be <= max_proportion")
        return self


class SuggestRequest(BaseModel):
    ingredients: list[SuggestIngredient] = Field(min_length=2)
    target: str = "volume"
    n_candidates: int = Field(default=5, ge=1, le=20)
    n_samples: int = Field(default=1000, ge=100, le=5000)
    fermentation_temp_c: float = Field(default=30.0, gt=0, le=60)
    fermentation_duration_min: float = Field(default=120.0, gt=0, le=1440)
    baking_temp_c: float = Field(default=200.0, gt=0, le=350)
    baking_duration_min: float = Field(default=25.0, gt=0, le=240)


class SuggestCandidate(BaseModel):
    proportions: dict[str, float]
    volume_increase_pct: float
    core_temp_c: float
    crust_temp_c: float


class SuggestResponse(BaseModel):
    candidates: list[SuggestCandidate]


@router.post("/suggest", response_model=SuggestResponse)
def suggest(body: SuggestRequest, db: Session = Depends(get_db)):
    ings = {i.id: i for i in db.query(Ingredient).all()}
    items = []
    for s in body.ingredients:
        ing = ings.get(s.ingredient_id)
        if not ing:
            continue
        items.append((ing, s.min_proportion, s.max_proportion))
    if len(items) < 2:
        return SuggestResponse(candidates=[])

    calc = BlendCalculator()
    fermenter = FermentationSimulator(FermentationParams(temp_c=body.fermentation_temp_c))
    baker = BakingSimulator(BakingParams(oven_temp_c=body.baking_temp_c, baking_time_min=body.baking_duration_min))

    candidates = []
    rng = random.Random()
    for _ in range(body.n_samples):
        props = _sample_bounded_proportions(items, rng, max_attempts=20)
        if props is None:
            break

        data = [(ing, p) for (ing, _, _), p in zip(items, props)]
        blend_props = calc.calculate(data)

        ferm_result = fermenter.simulate(viscosity_index=blend_props.viscosity_index, duration_min=body.fermentation_duration_min)
        bake_result = baker.simulate(gelatinization_temp_min=blend_props.gelatinization_temp_min, gelatinization_temp_max=blend_props.gelatinization_temp_max)

        candidates.append((
            {ing.name: round(p, 3) for (ing, _, _), p in zip(items, props)},
            ferm_result.final_volume_increase * 100,
            bake_result.core_temp_c,
            bake_result.crust_temp_c,
        ))

    key_idx = {"volume": 1, "core_temp": 2}.get(body.target, 1)
    candidates.sort(key=lambda c: c[key_idx], reverse=True)

    return SuggestResponse(candidates=[
        SuggestCandidate(proportions=p, volume_increase_pct=v, core_temp_c=c, crust_temp_c=cr)
        for p, v, c, cr in candidates[:body.n_candidates]
    ])


class ProcessRange(BaseModel):
    min: float = Field(gt=0)
    max: float = Field(gt=0)

    @model_validator(mode="after")
    def min_not_greater_than_max(self):
        if self.min > self.max:
            raise ValueError("min must be <= max")
        return self


class ApplicationSuggestRequest(BaseModel):
    application_id: int = Field(gt=0)
    ingredients: list[SuggestIngredient] = Field(min_length=2)
    n_candidates: int = Field(default=5, ge=1, le=20)
    n_blend_samples: int = Field(default=100, ge=10, le=2000)
    n_process_samples: int = Field(default=20, ge=5, le=200)
    seed: int | None = None
    fermentation_temp: ProcessRange = Field(default_factory=lambda: ProcessRange(min=20, max=40))
    fermentation_duration: ProcessRange = Field(default_factory=lambda: ProcessRange(min=60, max=240))
    baking_temp: ProcessRange = Field(default_factory=lambda: ProcessRange(min=170, max=240))
    baking_duration: ProcessRange = Field(default_factory=lambda: ProcessRange(min=20, max=50))
    w_process: float = Field(default=0.55, ge=0, le=1)
    w_blend: float = Field(default=0.25, ge=0, le=1)
    w_flavor: float = Field(default=0.20, ge=0, le=1)


class CandidateConfidenceResponse(BaseModel):
    score: float
    level: str
    basis: list[str]
    risk_flags: list[str]
    confidence_summary: str
    risk_warnings: list[dict[str, Any]]


class ApplicationBlendCandidate(BaseModel):
    rank: int
    score: float
    process_score: float
    blend_score: float
    flavor_score: float
    proportions: dict[str, float]
    process: dict[str, float]
    properties: dict[str, float]
    flavor_profile: dict[str, float]
    cooking_metrics: dict[str, Any] | None = None
    bread_metrics: dict[str, Any] | None = None
    model_confidence: CandidateConfidenceResponse
    coverage_diagnostics: dict[str, Any] | None = None
    volume_increase_pct: float
    core_temp_c: float
    crust_temp_c: float


class ApplicationSuggestResponse(BaseModel):
    application: str
    target_profile: str
    flavor_target: str
    preset_metadata: dict[str, Any] | None = None
    candidates: list[ApplicationBlendCandidate]


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


def _blend_values(props) -> dict[str, float]:
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


def _score_bread_quality(result: BreadQualityResult, profile) -> float:
    volume_score = math.exp(-0.5 * ((result.specific_volume_cm3_g - 2.5) / 0.6) ** 2)
    core_target = profile.core_target_c or 96.0
    core_score = math.exp(-0.5 * ((result.core_temp_c - core_target) / profile.core_sigma_c) ** 2)
    crust_score = math.exp(-0.5 * ((result.crust_temp_c - profile.crust_target_c) / profile.crust_sigma_c) ** 2)
    return float(0.45 * volume_score + 0.35 * core_score + 0.20 * crust_score)


@router.post("/application-suggest", response_model=ApplicationSuggestResponse)
def suggest_for_application(body: ApplicationSuggestRequest, db: Session = Depends(get_db)):
    application = db.query(Application).filter(Application.id == body.application_id).first()
    if not application:
        raise HTTPException(404, detail="Application not found")

    ings = {i.id: i for i in db.query(Ingredient).all()}
    items = []
    for s in body.ingredients:
        ing = ings.get(s.ingredient_id)
        if not ing:
            raise HTTPException(404, detail=f"Ingredient {s.ingredient_id} not found")
        if s.min_proportion > s.max_proportion:
            raise HTTPException(400, detail="min_proportion must be <= max_proportion")
        items.append((ing, s.min_proportion, s.max_proportion))

    rng = random.Random(body.seed)
    profile = get_sweep_target_profile(application.name)
    flavor_target = get_flavor_target(application.name)
    is_pasta = application.name.strip().lower() == "pasta fresca"
    is_bread = application.name.strip().lower() == "pane"
    weight_sum = body.w_process + body.w_blend + body.w_flavor
    if weight_sum <= 0:
        raise HTTPException(400, detail="At least one score weight must be positive")
    w_process = body.w_process / weight_sum
    w_blend = body.w_blend / weight_sum
    w_flavor = body.w_flavor / weight_sum
    calc = BlendCalculator()
    coverage_domain = domain_for_application(application.name)
    literature_coverage_summary = build_domain_coverage(db, coverage_domain) if coverage_domain else None
    sweeper = SimulationSweeper()
    baking_temp_range = body.baking_temp
    baking_duration_range = body.baking_duration
    if is_pasta and body.baking_temp.max > 120:
        baking_temp_range = ProcessRange(min=90, max=100)
    if is_pasta and body.baking_duration.max > 30:
        baking_duration_range = ProcessRange(min=4, max=14)

    process_points = sweeper.generate_random(
        SweepRange(body.fermentation_temp.min, body.fermentation_temp.max),
        SweepRange(body.fermentation_duration.min, body.fermentation_duration.max),
        SweepRange(baking_temp_range.min, baking_temp_range.max),
        SweepRange(baking_duration_range.min, baking_duration_range.max),
        n_samples=body.n_process_samples,
        seed=body.seed,
    )

    candidates = []
    attempts = 0
    while len(candidates) < body.n_blend_samples and attempts < body.n_blend_samples * 20:
        attempts += 1
        proportions = _sample_bounded_proportions(items, rng, max_attempts=20)
        if proportions is None:
            break

        blend_data = [(ing, prop) for (ing, _, _), prop in zip(items, proportions)]
        blend_props = calc.calculate(blend_data)

        cooking_metrics = None
        bread_metrics = None
        if is_pasta:
            best_cooking = None
            best_point = None
            best_params = None
            for point in process_points:
                params = pasta_v1_process_params(
                    blend_props,
                    water_temp_c=point["baking_temp_c"],
                    cooking_time_min=point["baking_duration_min"],
                )
                cooking = PastaCookingSimulator(params).simulate(blend_props)
                if best_cooking is None or cooking.quality_score > best_cooking.quality_score:
                    best_cooking = cooking
                    best_point = point
                    best_params = params
            if best_cooking is None or best_point is None or best_params is None:
                continue
            process_score = best_cooking.quality_score
            process_data = serialize_pasta_process_params(best_params)
            cooking_metrics = {
                "water_uptake_pct": best_cooking.water_uptake_pct,
                "cooking_loss_pct": best_cooking.cooking_loss_pct,
                "swelling_index": best_cooking.swelling_index,
                "firmness_index": best_cooking.firmness_index,
                "stickiness_index": best_cooking.stickiness_index,
                "quality_score": best_cooking.quality_score,
                "gelation_index": best_cooking.gelation_index,
                "pregelatinization_index": best_cooking.pregelatinization_index,
                "syneresis_index": best_cooking.syneresis_index,
                "starch_leaching_index": best_cooking.starch_leaching_index,
                "process_family": best_cooking.process_family,
                "calibration_confidence": best_cooking.calibration_confidence,
                "calibration_score": best_cooking.calibration_score,
                "calibration_notes": best_cooking.calibration_notes,
            }
            volume_pct = 0.0
            core_temp = best_cooking.core_temp_c
            crust_temp = best_point["baking_temp_c"]
        elif is_bread:
            best_bread = None
            best_point = None
            best_score = -1.0
            for point in process_points:
                bread = BreadQualitySimulator(
                    BreadQualityParams(
                        fermentation_temp_c=point["fermentation_temp_c"],
                        fermentation_time_min=point["fermentation_duration_min"],
                        baking_temp_c=point["baking_temp_c"],
                        baking_time_min=point["baking_duration_min"],
                    )
                ).simulate(blend_props)
                candidate_score = _score_bread_quality(bread, profile)
                if best_bread is None or candidate_score > best_score:
                    best_bread = bread
                    best_point = point
                    best_score = candidate_score
            if best_bread is None or best_point is None:
                continue
            process_score = best_score
            process_data = best_point
            bread_metrics = _serialize_bread_metrics(best_bread)
            fermentation = FermentationSimulator(
                FermentationParams(temp_c=best_point["fermentation_temp_c"])
            ).simulate(
                viscosity_index=blend_props.viscosity_index,
                duration_min=best_point["fermentation_duration_min"],
            )
            volume_pct = round(fermentation.final_volume_increase * 100, 2)
            core_temp = best_bread.core_temp_c
            crust_temp = best_bread.crust_temp_c
        else:
            sweep = sweeper.run_sweep(
                blend_props,
                process_points,
                top_n=1,
                target_profile=profile,
            )
            if not sweep.points:
                continue
            best_process = sweep.points[0]
            process_score = best_process.composite_score
            process_data = {
                "fermentation_temp_c": best_process.fermentation_temp_c,
                "fermentation_duration_min": best_process.fermentation_duration_min,
                "baking_temp_c": best_process.baking_temp_c,
                "baking_duration_min": best_process.baking_duration_min,
            }
            volume_pct = round(best_process.volume_increase * 100, 2)
            core_temp = best_process.core_temp_c
            crust_temp = best_process.crust_temp_c

        blend_score = score_blend_against_profile(_blend_values(blend_props), profile)
        flavor_profile = calculate_blend_flavor(blend_data)
        flavor_score = score_flavor_against_target(flavor_profile, flavor_target)
        total_score = w_process * process_score + w_blend * blend_score + w_flavor * flavor_score
        blend_values = _blend_values(blend_props)
        ingredient_names = [
            ing.name
            for (ing, _, _), prop in zip(items, proportions)
            if prop > 1e-6
        ]
        literature_coverage = assess_literature_coverage(
            application=application.name,
            ingredient_names=ingredient_names,
            blend_values=blend_values,
            process_values=process_data,
            summary=literature_coverage_summary,
        ).as_dict()
        coverage_diagnostics = None
        if is_pizza_v1_application(application.name):
            pizza_diagnostics = assess_pizza_v1_coverage(
                ingredient_names=ingredient_names,
                blend_values=blend_values,
                process_values=process_data,
            )
            coverage_diagnostics = pizza_diagnostics.as_dict()
            literature_coverage = pizza_diagnostics.as_literature_coverage()
            total_score *= pizza_diagnostics.coverage_fraction
        model_confidence = serialize_candidate_confidence(assess_candidate_confidence(
            blend_values=blend_values,
            profile=profile,
            process_score=process_score,
            blend_score=blend_score,
            flavor_score=flavor_score,
            cooking_metrics=cooking_metrics,
            bread_metrics=bread_metrics,
            literature_coverage=literature_coverage,
        ))

        candidates.append((
            total_score,
            process_score,
            blend_score,
            flavor_score,
            proportions,
            blend_props,
            flavor_profile,
            process_data,
            volume_pct,
            core_temp,
            crust_temp,
            cooking_metrics,
            bread_metrics,
            model_confidence,
            coverage_diagnostics,
        ))

    candidates.sort(key=lambda c: c[0], reverse=True)

    return ApplicationSuggestResponse(
        application=application.name,
        target_profile=profile.name,
        flavor_target=flavor_target.name,
        preset_metadata={
            "preset": "pizza-v1-compatible",
            "audit_doc": "docs/pizza-v1-literature-audit.md",
            "evidence_level": "literature_informed_boundaries_only",
        } if is_pizza_v1_application(application.name) else None,
        candidates=[
            ApplicationBlendCandidate(
                rank=rank,
                score=round(total_score, 4),
                process_score=round(process_score, 4),
                blend_score=round(blend_score, 4),
                flavor_score=round(flavor_score, 4),
                proportions={
                    ing.name: round(prop, 4)
                    for (ing, _, _), prop in zip(items, proportions)
                },
                process=process_data,
                properties={key: round(value, 4) for key, value in _blend_values(blend_props).items()},
                flavor_profile=flavor_profile,
                cooking_metrics=cooking_metrics,
                bread_metrics=bread_metrics,
                model_confidence=model_confidence,
                coverage_diagnostics=coverage_diagnostics,
                volume_increase_pct=volume_pct,
                core_temp_c=core_temp,
                crust_temp_c=crust_temp,
            )
            for rank, (
                total_score,
                process_score,
                blend_score,
                flavor_score,
                proportions,
                blend_props,
                flavor_profile,
                process_data,
                volume_pct,
                core_temp,
                crust_temp,
                cooking_metrics,
                bread_metrics,
                model_confidence,
                coverage_diagnostics,
            )
            in enumerate(candidates[:body.n_candidates], start=1)
        ],
    )
