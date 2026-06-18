import random

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from glutenix.api.deps import get_db, get_gpr
from glutenix.bo.explain import ard_feature_importance
from glutenix.db.models import Application, Ingredient
from glutenix.engine.baking import BakingParams, BakingSimulator
from glutenix.engine.blend import BlendCalculator
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


class SuggestRequest(BaseModel):
    ingredients: list[SuggestIngredient] = Field(min_length=2)
    target: str = "volume"
    n_candidates: int = Field(default=5, ge=1, le=20)
    n_samples: int = Field(default=1000, ge=100, le=5000)
    fermentation_temp_c: float = 30.0
    fermentation_duration_min: float = 120.0
    baking_temp_c: float = 200.0
    baking_duration_min: float = 25.0


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
    for _ in range(body.n_samples):
        raw = [random.uniform(lo, hi) for _, lo, hi in items]
        total = sum(raw)
        if total == 0:
            continue
        props = [r / total for r in raw]

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
    min: float
    max: float


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
    volume_increase_pct: float
    core_temp_c: float
    crust_temp_c: float


class ApplicationSuggestResponse(BaseModel):
    application: str
    target_profile: str
    flavor_target: str
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
    weight_sum = body.w_process + body.w_blend + body.w_flavor
    if weight_sum <= 0:
        raise HTTPException(400, detail="At least one score weight must be positive")
    w_process = body.w_process / weight_sum
    w_blend = body.w_blend / weight_sum
    w_flavor = body.w_flavor / weight_sum
    calc = BlendCalculator()
    sweeper = SimulationSweeper()
    process_points = sweeper.generate_random(
        SweepRange(body.fermentation_temp.min, body.fermentation_temp.max),
        SweepRange(body.fermentation_duration.min, body.fermentation_duration.max),
        SweepRange(body.baking_temp.min, body.baking_temp.max),
        SweepRange(body.baking_duration.min, body.baking_duration.max),
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
        sweep = sweeper.run_sweep(
            blend_props,
            process_points,
            top_n=1,
            target_profile=profile,
        )
        if not sweep.points:
            continue

        blend_score = score_blend_against_profile(_blend_values(blend_props), profile)
        flavor_profile = calculate_blend_flavor(blend_data)
        flavor_score = score_flavor_against_target(flavor_profile, flavor_target)
        best_process = sweep.points[0]
        process_score = best_process.composite_score
        total_score = w_process * process_score + w_blend * blend_score + w_flavor * flavor_score

        candidates.append((
            total_score,
            process_score,
            blend_score,
            flavor_score,
            proportions,
            blend_props,
            flavor_profile,
            best_process,
        ))

    candidates.sort(key=lambda c: c[0], reverse=True)

    return ApplicationSuggestResponse(
        application=application.name,
        target_profile=profile.name,
        flavor_target=flavor_target.name,
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
                process={
                    "fermentation_temp_c": best.fermentation_temp_c,
                    "fermentation_duration_min": best.fermentation_duration_min,
                    "baking_temp_c": best.baking_temp_c,
                    "baking_duration_min": best.baking_duration_min,
                },
                properties={key: round(value, 4) for key, value in _blend_values(blend_props).items()},
                flavor_profile=flavor_profile,
                volume_increase_pct=round(best.volume_increase * 100, 2),
                core_temp_c=best.core_temp_c,
                crust_temp_c=best.crust_temp_c,
            )
            for rank, (
                total_score,
                process_score,
                blend_score,
                flavor_score,
                proportions,
                blend_props,
                flavor_profile,
                best,
            )
            in enumerate(candidates[:body.n_candidates], start=1)
        ],
    )
