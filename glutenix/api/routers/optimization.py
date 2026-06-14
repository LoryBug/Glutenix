from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from glutenix.api.deps import get_db, get_gpr
from glutenix.bo.explain import ard_feature_importance
from glutenix.db.models import Ingredient
from glutenix.engine.baking import BakingParams, BakingSimulator
from glutenix.engine.blend import BlendCalculator
from glutenix.engine.fermentation import FermentationParams, FermentationSimulator
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
    import random

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
