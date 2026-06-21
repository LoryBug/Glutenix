import json
import math
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from glutenix.api.deps import get_db
from glutenix.calibration.coverage import (
    assess_literature_coverage,
    build_domain_coverage,
    domain_for_application,
)
from glutenix.db.models import (
    Application,
    Blend,
    BlendIngredient,
    ExperimentResult,
    Ingredient,
    SimulationCandidate,
    SimulationRun,
)
from glutenix.engine.blend import BlendCalculator, BlendProperties
from glutenix.engine.bread import BreadQualityParams, BreadQualityResult, BreadQualitySimulator
from glutenix.engine.confidence import assess_candidate_confidence, serialize_candidate_confidence
from glutenix.engine.cooking import PastaCookingParams, PastaCookingSimulator
from glutenix.engine.fermentation import FermentationParams, FermentationSimulator
from glutenix.engine.flavor import calculate_blend_flavor, get_flavor_target, score_flavor_against_target
from glutenix.engine.sweep import SimulationSweeper, SweepRange
from glutenix.engine.targets import get_sweep_target_profile, score_blend_against_profile

router = APIRouter(tags=["internal"])


class CandidateResponse(BaseModel):
    id: int
    run_id: int
    rank: int
    status: str
    score: float
    process_score: float | None
    blend_score: float | None
    flavor_score: float | None
    proportions: dict[str, float]
    process: dict[str, Any]
    properties: dict[str, Any]
    metrics: dict[str, Any]
    confidence: dict[str, Any]
    risk_flags: list[str]
    decision_notes: str | None


class RunSummaryResponse(BaseModel):
    id: int
    application_name: str
    source: str
    preset: str | None
    seed: int | None
    blend_samples: int | None
    process_samples: int | None
    top_n: int | None
    status: str
    notes: str | None
    created_at: str
    top_score: float | None
    candidate_count: int


class RunDetailResponse(RunSummaryResponse):
    process_bounds: dict[str, Any] | None
    parameters: dict[str, Any] | None
    candidates: list[CandidateResponse]


class CandidateUpdateRequest(BaseModel):
    status: str = Field(pattern="^(new|promising|avoid|test_next|tested|archived)$")
    notes: str | None = None


class PromoteCandidateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    description: str | None = None


class PromoteCandidateResponse(BaseModel):
    blend_id: int
    candidate_id: int
    name: str
    created: bool


class ExperimentFromCandidateRequest(BaseModel):
    candidate_id: int = Field(gt=0)
    blend_id: int | None = Field(default=None, gt=0)
    blend_name: str | None = Field(default=None, max_length=100)
    conditions: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any]


class ExperimentFromCandidateResponse(BaseModel):
    id: int
    blend_id: int
    candidate_id: int
    conditions: dict[str, Any]
    metrics: dict[str, Any]
    created_at: str


class ProcessRangeRequest(BaseModel):
    min: float = Field(gt=0)
    max: float = Field(gt=0)

    @model_validator(mode="after")
    def min_not_greater_than_max(self):
        if self.min > self.max:
            raise ValueError("min must be <= max")
        return self


class CompareWeights(BaseModel):
    process: float = Field(default=0.55, ge=0)
    blend: float = Field(default=0.25, ge=0)
    flavor: float = Field(default=0.20, ge=0)

    @model_validator(mode="after")
    def at_least_one_weight(self):
        if self.process + self.blend + self.flavor <= 0:
            raise ValueError("At least one score weight must be positive")
        return self


class CompareItemRequest(BaseModel):
    candidate_id: int | None = Field(default=None, gt=0)
    blend_id: int | None = Field(default=None, gt=0)
    name: str | None = None
    proportions: dict[str, float] | None = None

    @model_validator(mode="after")
    def exactly_one_source(self):
        sources = [self.candidate_id is not None, self.blend_id is not None, self.proportions is not None]
        if sum(sources) != 1:
            raise ValueError("Provide exactly one of candidate_id, blend_id, or proportions")
        if self.proportions is not None:
            total = sum(self.proportions.values())
            if abs(total - 1.0) > 1e-3:
                raise ValueError(f"Custom proportions must sum to 1, got {total}")
            if any(value <= 0 for value in self.proportions.values()):
                raise ValueError("Custom proportions must be positive")
        return self


class BlendCompareRequest(BaseModel):
    application: str = "Pane"
    items: list[CompareItemRequest] = Field(min_length=2)
    n_process_samples: int = Field(default=40, ge=1, le=500)
    seed: int | None = None
    fermentation_temp: ProcessRangeRequest = Field(default_factory=lambda: ProcessRangeRequest(min=20, max=40))
    fermentation_duration: ProcessRangeRequest = Field(default_factory=lambda: ProcessRangeRequest(min=60, max=240))
    baking_temp: ProcessRangeRequest = Field(default_factory=lambda: ProcessRangeRequest(min=170, max=240))
    baking_duration: ProcessRangeRequest = Field(default_factory=lambda: ProcessRangeRequest(min=20, max=50))
    weights: CompareWeights = Field(default_factory=CompareWeights)


class BlendComparisonItemResponse(BaseModel):
    rank: int
    name: str
    source: dict[str, int | str]
    score: float
    process_score: float
    blend_score: float
    flavor_score: float
    delta_vs_best: float
    proportions: dict[str, float]
    process: dict[str, float]
    properties: dict[str, float]
    flavor_profile: dict[str, float]
    cooking_metrics: dict[str, Any] | None = None
    bread_metrics: dict[str, Any] | None = None
    model_confidence: dict[str, Any]


class BlendCompareResponse(BaseModel):
    application: str
    target_profile: str
    flavor_target: str
    ranking: list[BlendComparisonItemResponse]


@router.get("/simulation-runs", response_model=list[RunSummaryResponse])
def list_simulation_runs(limit: int = 20, db: Session = Depends(get_db)):
    runs = (
        db.query(SimulationRun)
        .order_by(SimulationRun.created_at.desc(), SimulationRun.id.desc())
        .limit(limit)
        .all()
    )
    return [_run_summary(run) for run in runs]


@router.get("/simulation-runs/{run_id}", response_model=RunDetailResponse)
def get_simulation_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(SimulationRun, run_id)
    if run is None:
        raise HTTPException(404, detail="Simulation run not found")
    return RunDetailResponse(
        **_run_summary(run).model_dump(),
        process_bounds=_json_or_none(run.process_bounds),
        parameters=_json_or_none(run.parameters),
        candidates=[_candidate_response(candidate) for candidate in run.candidates],
    )


@router.patch("/simulation-candidates/{candidate_id}", response_model=CandidateResponse)
def update_simulation_candidate(
    candidate_id: int,
    body: CandidateUpdateRequest,
    db: Session = Depends(get_db),
):
    candidate = db.get(SimulationCandidate, candidate_id)
    if candidate is None:
        raise HTTPException(404, detail="Simulation candidate not found")
    candidate.status = body.status
    if body.notes is not None:
        candidate.decision_notes = body.notes
    db.commit()
    db.refresh(candidate)
    return _candidate_response(candidate)


@router.post("/simulation-candidates/{candidate_id}/promote-blend", response_model=PromoteCandidateResponse)
def promote_simulation_candidate(
    candidate_id: int,
    body: PromoteCandidateRequest,
    db: Session = Depends(get_db),
):
    candidate = db.get(SimulationCandidate, candidate_id)
    if candidate is None:
        raise HTTPException(404, detail="Simulation candidate not found")
    blend, created = _promote_candidate_to_blend(db, candidate, body.name, body.description)
    return PromoteCandidateResponse(
        blend_id=blend.id,
        candidate_id=candidate.id,
        name=blend.name,
        created=created,
    )


@router.post("/experiments/from-candidate", response_model=ExperimentFromCandidateResponse, status_code=201)
def create_experiment_from_candidate(
    body: ExperimentFromCandidateRequest,
    db: Session = Depends(get_db),
):
    candidate = db.get(SimulationCandidate, body.candidate_id)
    if candidate is None:
        raise HTTPException(404, detail="Simulation candidate not found")

    if body.blend_id is not None:
        blend = db.get(Blend, body.blend_id)
        if blend is None:
            raise HTTPException(404, detail="Blend not found")
    else:
        blend, _ = _promote_candidate_to_blend(db, candidate, body.blend_name, None)

    conditions = {
        "candidate_id": candidate.id,
        "simulation_run_id": candidate.run_id,
        **body.conditions,
    }
    experiment = ExperimentResult(
        blend_id=blend.id,
        application_id=candidate.run.application_id,
        conditions=json.dumps(conditions, sort_keys=True),
        metrics=json.dumps(body.metrics, sort_keys=True),
    )
    db.add(experiment)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, detail="Experiment could not be created") from exc
    db.refresh(experiment)
    return ExperimentFromCandidateResponse(
        id=experiment.id,
        blend_id=blend.id,
        candidate_id=candidate.id,
        conditions=conditions,
        metrics=body.metrics,
        created_at=experiment.created_at.isoformat(),
    )


@router.post("/compare/blends", response_model=BlendCompareResponse)
def compare_blends(body: BlendCompareRequest, db: Session = Depends(get_db)):
    application = db.query(Application).filter(Application.name == body.application).first()
    if application is None:
        raise HTTPException(404, detail="Application not found")

    profile = get_sweep_target_profile(application.name)
    flavor_target = get_flavor_target(application.name)
    process_points = _process_points(body)
    weight_sum = body.weights.process + body.weights.blend + body.weights.flavor
    weights = {
        "process": body.weights.process / weight_sum,
        "blend": body.weights.blend / weight_sum,
        "flavor": body.weights.flavor / weight_sum,
    }
    coverage_domain = domain_for_application(application.name)
    coverage_summary = build_domain_coverage(db, coverage_domain) if coverage_domain else None

    rows = []
    for item in body.items:
        name, source, blend_data = _resolve_compare_item(db, item)
        row = _score_compare_item(
            application=application.name,
            name=name,
            source=source,
            blend_data=blend_data,
            process_points=process_points,
            profile=profile,
            flavor_target=flavor_target,
            coverage_summary=coverage_summary,
            weights=weights,
        )
        rows.append(row)

    rows.sort(key=lambda row: row["score"], reverse=True)
    best_score = rows[0]["score"] if rows else 0.0
    return BlendCompareResponse(
        application=application.name,
        target_profile=profile.name,
        flavor_target=flavor_target.name,
        ranking=[
            BlendComparisonItemResponse(
                rank=rank,
                delta_vs_best=round(best_score - row["score"], 4),
                **row,
            )
            for rank, row in enumerate(rows, start=1)
        ],
    )


def _run_summary(run: SimulationRun) -> RunSummaryResponse:
    return RunSummaryResponse(
        id=run.id,
        application_name=run.application_name,
        source=run.source,
        preset=run.preset,
        seed=run.seed,
        blend_samples=run.blend_samples,
        process_samples=run.process_samples,
        top_n=run.top_n,
        status=run.status,
        notes=run.notes,
        created_at=run.created_at.isoformat(),
        top_score=run.candidates[0].score if run.candidates else None,
        candidate_count=len(run.candidates),
    )


def _candidate_response(candidate: SimulationCandidate) -> CandidateResponse:
    return CandidateResponse(
        id=candidate.id,
        run_id=candidate.run_id,
        rank=candidate.rank,
        status=candidate.status,
        score=candidate.score,
        process_score=candidate.process_score,
        blend_score=candidate.blend_score,
        flavor_score=candidate.flavor_score,
        proportions=json.loads(candidate.proportions),
        process=json.loads(candidate.process),
        properties=json.loads(candidate.properties),
        metrics=json.loads(candidate.metrics),
        confidence=json.loads(candidate.confidence),
        risk_flags=json.loads(candidate.risk_flags or "[]"),
        decision_notes=candidate.decision_notes,
    )


def _json_or_none(value: str | None) -> dict[str, Any] | None:
    return json.loads(value) if value else None


def _promote_candidate_to_blend(
    db: Session,
    candidate: SimulationCandidate,
    name: str | None,
    description: str | None,
) -> tuple[Blend, bool]:
    blend_name = name or f"Physical test candidate {candidate.id}"
    existing = db.query(Blend).filter(Blend.name == blend_name).first()
    if existing is not None:
        if name is not None:
            raise HTTPException(409, detail="Blend name already exists")
        return existing, False

    application_id = candidate.run.application_id
    blend = Blend(
        name=blend_name,
        description=description or (
            f"Promoted from simulation candidate #{candidate.id}, run #{candidate.run_id}; "
            f"status={candidate.status}; score={candidate.score}."
        ),
        application_id=application_id,
    )
    db.add(blend)
    db.flush()

    ingredients = {ingredient.name: ingredient for ingredient in db.query(Ingredient).all()}
    for ingredient_name, proportion in json.loads(candidate.proportions).items():
        ingredient = ingredients.get(ingredient_name)
        if ingredient is None:
            raise HTTPException(404, detail=f"Ingredient not found: {ingredient_name}")
        db.add(BlendIngredient(
            blend_id=blend.id,
            ingredient_id=ingredient.id,
            proportion=proportion,
        ))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, detail="Blend could not be created") from exc
    db.refresh(blend)
    return blend, True


def _process_points(body: BlendCompareRequest) -> list[dict[str, float]]:
    baking_temp = body.baking_temp
    baking_duration = body.baking_duration
    if body.application.strip().lower() == "pasta fresca":
        baking_temp = ProcessRangeRequest(min=90, max=100) if baking_temp.max > 120 else baking_temp
        baking_duration = ProcessRangeRequest(min=4, max=14) if baking_duration.max > 30 else baking_duration
    return SimulationSweeper().generate_random(
        SweepRange(body.fermentation_temp.min, body.fermentation_temp.max),
        SweepRange(body.fermentation_duration.min, body.fermentation_duration.max),
        SweepRange(baking_temp.min, baking_temp.max),
        SweepRange(baking_duration.min, baking_duration.max),
        n_samples=body.n_process_samples,
        seed=body.seed,
    )


def _resolve_compare_item(
    db: Session,
    item: CompareItemRequest,
) -> tuple[str, dict[str, int | str], list[tuple[Ingredient, float]]]:
    if item.candidate_id is not None:
        candidate = db.get(SimulationCandidate, item.candidate_id)
        if candidate is None:
            raise HTTPException(404, detail=f"Simulation candidate not found: {item.candidate_id}")
        return (
            item.name or f"candidate #{candidate.id}",
            {"type": "candidate", "id": candidate.id},
            _blend_data_from_proportions(db, json.loads(candidate.proportions)),
        )
    if item.blend_id is not None:
        blend = db.get(Blend, item.blend_id)
        if blend is None:
            raise HTTPException(404, detail=f"Blend not found: {item.blend_id}")
        return (
            item.name or blend.name,
            {"type": "blend", "id": blend.id},
            [(blend_ingredient.ingredient, blend_ingredient.proportion) for blend_ingredient in blend.ingredients],
        )
    assert item.proportions is not None
    return (
        item.name or "custom blend",
        {"type": "custom", "id": item.name or "custom blend"},
        _blend_data_from_proportions(db, item.proportions),
    )


def _blend_data_from_proportions(
    db: Session,
    proportions: dict[str, float],
) -> list[tuple[Ingredient, float]]:
    ingredients = {ingredient.name: ingredient for ingredient in db.query(Ingredient).all()}
    missing = sorted(set(proportions) - set(ingredients))
    if missing:
        raise HTTPException(404, detail=f"Ingredients not found: {missing}")
    return [(ingredients[name], proportion) for name, proportion in proportions.items()]


def _normalize_blend_data(blend_data: list[tuple[Ingredient, float]]) -> list[tuple[Ingredient, float]]:
    total = sum(proportion for _, proportion in blend_data)
    if total <= 0:
        raise HTTPException(400, detail="Blend proportions must sum to a positive value")
    if abs(total - 1.0) > 1e-3:
        raise HTTPException(400, detail=f"Blend proportions must sum to 1.0, got {total}")
    return [(ingredient, proportion / total) for ingredient, proportion in blend_data]


def _score_compare_item(
    *,
    application: str,
    name: str,
    source: dict[str, int | str],
    blend_data: list[tuple[Ingredient, float]],
    process_points: list[dict[str, float]],
    profile,
    flavor_target,
    coverage_summary,
    weights: dict[str, float],
) -> dict[str, Any]:
    blend_data = _normalize_blend_data(blend_data)
    blend_props = BlendCalculator().calculate(blend_data)
    blend_values = _blend_values(blend_props)
    flavor_profile = calculate_blend_flavor(blend_data)
    flavor_score = score_flavor_against_target(flavor_profile, flavor_target)
    blend_score = score_blend_against_profile(blend_values, profile)
    cooking_metrics = None
    bread_metrics = None

    if application.strip().lower() == "pasta fresca":
        process_score, process_data, cooking_metrics, _volume_pct, _core_temp, _crust_temp = _best_pasta_process(
            blend_props,
            process_points,
        )
    elif application.strip().lower() == "pane":
        process_score, process_data, bread_metrics, _volume_pct, _core_temp, _crust_temp = _best_bread_process(
            blend_props,
            process_points,
            profile,
        )
    else:
        process_score, process_data, _volume_pct, _core_temp, _crust_temp = _best_generic_process(
            blend_props,
            process_points,
            profile,
        )

    total_score = weights["process"] * process_score + weights["blend"] * blend_score + weights["flavor"] * flavor_score
    literature_coverage = assess_literature_coverage(
        application=application,
        ingredient_names=[ingredient.name for ingredient, proportion in blend_data if proportion > 1e-6],
        blend_values=blend_values,
        process_values=process_data,
        summary=coverage_summary,
    ).as_dict()
    confidence = serialize_candidate_confidence(assess_candidate_confidence(
        blend_values=blend_values,
        profile=profile,
        process_score=process_score,
        blend_score=blend_score,
        flavor_score=flavor_score,
        cooking_metrics=cooking_metrics,
        bread_metrics=bread_metrics,
        literature_coverage=literature_coverage,
    ))

    return {
        "name": name,
        "source": source,
        "score": round(total_score, 4),
        "process_score": round(process_score, 4),
        "blend_score": round(blend_score, 4),
        "flavor_score": round(flavor_score, 4),
        "proportions": {ingredient.name: round(proportion, 4) for ingredient, proportion in blend_data},
        "process": {key: round(value, 4) for key, value in process_data.items()},
        "properties": {key: round(value, 4) for key, value in blend_values.items()},
        "flavor_profile": flavor_profile,
        "cooking_metrics": cooking_metrics,
        "bread_metrics": bread_metrics,
        "model_confidence": confidence,
    }


def _best_pasta_process(
    blend_props: BlendProperties,
    process_points: list[dict[str, float]],
) -> tuple[float, dict[str, float], dict[str, Any], float, float, float]:
    best_cooking = None
    best_point = None
    for point in process_points:
        cooking = PastaCookingSimulator(PastaCookingParams(
            water_temp_c=point["baking_temp_c"],
            cooking_time_min=point["baking_duration_min"],
            water_to_flour_ratio=0.9,
        )).simulate(blend_props)
        if best_cooking is None or cooking.quality_score > best_cooking.quality_score:
            best_cooking = cooking
            best_point = point
    if best_cooking is None or best_point is None:
        raise HTTPException(400, detail="No process points generated")
    process_data = {
        "water_temp_c": best_point["baking_temp_c"],
        "cooking_time_min": best_point["baking_duration_min"],
        "pasta_thickness_mm": 2.0,
        "water_to_flour_ratio": 0.9,
    }
    metrics = {
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
    return best_cooking.quality_score, process_data, metrics, 0.0, best_cooking.core_temp_c, best_point["baking_temp_c"]


def _best_bread_process(
    blend_props: BlendProperties,
    process_points: list[dict[str, float]],
    profile,
) -> tuple[float, dict[str, float], dict[str, Any], float, float, float]:
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
        raise HTTPException(400, detail="No process points generated")
    fermentation = FermentationSimulator(FermentationParams(temp_c=best_point["fermentation_temp_c"])).simulate(
        viscosity_index=blend_props.viscosity_index,
        duration_min=best_point["fermentation_duration_min"],
    )
    return (
        best_score,
        best_point,
        _serialize_bread_metrics(best_bread),
        round(fermentation.final_volume_increase * 100, 2),
        best_bread.core_temp_c,
        best_bread.crust_temp_c,
    )


def _best_generic_process(
    blend_props: BlendProperties,
    process_points: list[dict[str, float]],
    profile,
) -> tuple[float, dict[str, float], float, float, float]:
    sweep = SimulationSweeper().run_sweep(blend_props, process_points, top_n=1, target_profile=profile)
    if not sweep.points:
        raise HTTPException(400, detail="No process points generated")
    point = sweep.points[0]
    return (
        point.composite_score,
        {
            "fermentation_temp_c": point.fermentation_temp_c,
            "fermentation_duration_min": point.fermentation_duration_min,
            "baking_temp_c": point.baking_temp_c,
            "baking_duration_min": point.baking_duration_min,
        },
        round(point.volume_increase * 100, 2),
        point.core_temp_c,
        point.crust_temp_c,
    )


def _score_bread_quality(result: BreadQualityResult, profile) -> float:
    volume_score = math.exp(-0.5 * ((result.specific_volume_cm3_g - 2.5) / 0.6) ** 2)
    core_target = profile.core_target_c or 96.0
    core_score = math.exp(-0.5 * ((result.core_temp_c - core_target) / profile.core_sigma_c) ** 2)
    crust_score = math.exp(-0.5 * ((result.crust_temp_c - profile.crust_target_c) / profile.crust_sigma_c) ** 2)
    return float(0.45 * volume_score + 0.35 * core_score + 0.20 * crust_score)


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
