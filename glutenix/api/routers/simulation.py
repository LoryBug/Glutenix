from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from glutenix.api.deps import get_db
from glutenix.db.models import Application, Blend, SimulationResult
from glutenix.engine.baking import BakingParams, BakingSimulator
from glutenix.engine.blend import BlendCalculator
from glutenix.engine.fermentation import FermentationParams, FermentationSimulator
from glutenix.engine.sweep import SimulationSweeper, SweepRange
from glutenix.engine.targets import (
    DEFAULT_SWEEP_PROFILE,
    SWEEP_TARGET_PROFILES,
    get_sweep_target_profile,
    serialize_sweep_target_profile,
)

router = APIRouter(prefix="/simulate", tags=["simulation"])


class TargetBlendRangeSchema(BaseModel):
    min: float
    max: float
    weight: float


class SweepTargetProfileSchema(BaseModel):
    name: str
    volume_target: float
    volume_sigma: float
    core_target_c: float | None
    core_offset_from_gel_max_c: float
    core_sigma_c: float
    crust_target_c: float
    crust_sigma_c: float
    efficiency_start_min: float
    efficiency_window_min: float
    evidence_level: str
    rationale: str
    sources: list[str]
    blend_ranges: dict[str, TargetBlendRangeSchema]


@router.get("")
def list_simulations(db: Session = Depends(get_db)):
    results = db.query(SimulationResult).order_by(SimulationResult.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "blend_id": r.blend_id,
            "results": r.results,
            "created_at": r.created_at.isoformat(),
        }
        for r in results
    ]


@router.get("/target-profiles", response_model=list[SweepTargetProfileSchema])
def list_target_profiles():
    profiles = [DEFAULT_SWEEP_PROFILE, *SWEEP_TARGET_PROFILES.values()]
    return [serialize_sweep_target_profile(profile) for profile in profiles]


@router.get("/{simulation_id}")
def get_simulation(simulation_id: int, db: Session = Depends(get_db)):
    r = db.query(SimulationResult).filter(SimulationResult.id == simulation_id).first()
    if not r:
        raise HTTPException(404, detail="Simulation not found")
    return {
        "id": r.id,
        "blend_id": r.blend_id,
        "results": r.results,
        "created_at": r.created_at.isoformat(),
    }


class SimulateRequest(BaseModel):
    blend_id: int
    fermentation_temp_c: float = 30.0
    fermentation_duration_min: float = 120.0
    baking_temp_c: float = 200.0
    baking_duration_min: float = 25.0


class SimulateResponse(BaseModel):
    protein_pct: float
    starch_pct: float
    fat_pct: float
    fiber_pct: float
    water_absorption: float
    viscosity_index: float
    hydrocolloid_pct: float
    gelatinization_temp_min: float
    gelatinization_temp_max: float
    amylose_pct: float
    fermentation_volume_increase: float
    baking_core_temp_c: float
    baking_crust_temp_c: float


@router.post("", response_model=SimulateResponse)
def simulate(body: SimulateRequest, db: Session = Depends(get_db)):
    blend = db.query(Blend).filter(Blend.id == body.blend_id).first()
    if not blend:
        raise HTTPException(404, detail="Blend not found")
    if not blend.ingredients:
        raise HTTPException(400, detail="Blend has no ingredients")

    calc = BlendCalculator()
    props = calc.calculate(
        [(bi.ingredient, bi.proportion) for bi in blend.ingredients]
    )

    fermenter = FermentationSimulator(
        FermentationParams(temp_c=body.fermentation_temp_c)
    )
    ferm_result = fermenter.simulate(
        viscosity_index=props.viscosity_index,
        duration_min=body.fermentation_duration_min,
    )

    baker = BakingSimulator(
        BakingParams(
            oven_temp_c=body.baking_temp_c,
            baking_time_min=body.baking_duration_min,
        )
    )
    bake_result = baker.simulate(
        gelatinization_temp_min=props.gelatinization_temp_min,
        gelatinization_temp_max=props.gelatinization_temp_max,
    )

    result = SimulateResponse(
        protein_pct=props.protein_pct,
        starch_pct=props.starch_pct,
        fat_pct=props.fat_pct,
        fiber_pct=props.fiber_pct,
        water_absorption=props.water_absorption,
        viscosity_index=props.viscosity_index,
        hydrocolloid_pct=props.hydrocolloid_pct,
        gelatinization_temp_min=props.gelatinization_temp_min,
        gelatinization_temp_max=props.gelatinization_temp_max,
        amylose_pct=props.amylose_pct,
        fermentation_volume_increase=round(float(ferm_result.final_volume_increase), 4),
        baking_core_temp_c=round(float(bake_result.core_temp_c), 2),
        baking_crust_temp_c=round(float(bake_result.crust_temp_c), 2),
    )

    db.add(
        SimulationResult(
            blend_id=body.blend_id,
            results=result.model_dump_json(),
        )
    )
    db.commit()

    return result


class SweepRangeSchema(BaseModel):
    min: float
    max: float
    step: float | None = None
    n: int | None = None


class SweepRequest(BaseModel):
    blend_id: int
    application_id: int | None = Field(default=None, gt=0)
    strategy: str = Field(default="random", pattern="^(grid|random)$")
    n_samples: int = Field(default=200, ge=10, le=10000)
    top_n: int = Field(default=10, ge=1, le=100)
    seed: int | None = None

    fermentation_temp: SweepRangeSchema = Field(
        default_factory=lambda: SweepRangeSchema(min=25, max=35, step=2.5)
    )
    fermentation_duration: SweepRangeSchema = Field(
        default_factory=lambda: SweepRangeSchema(min=60, max=180, step=20)
    )
    baking_temp: SweepRangeSchema = Field(
        default_factory=lambda: SweepRangeSchema(min=180, max=220, step=10)
    )
    baking_duration: SweepRangeSchema = Field(
        default_factory=lambda: SweepRangeSchema(min=15, max=35, step=5)
    )

    w_volume: float = Field(default=0.30, ge=0, le=1)
    w_gelatinization: float = Field(default=0.40, ge=0, le=1)
    w_crust: float = Field(default=0.20, ge=0, le=1)
    w_efficiency: float = Field(default=0.10, ge=0, le=1)


class SweepPointSchema(BaseModel):
    fermentation_temp_c: float
    fermentation_duration_min: float
    baking_temp_c: float
    baking_duration_min: float
    volume_increase: float
    core_temp_c: float
    crust_temp_c: float
    composite_score: float


class SweepResponse(BaseModel):
    points: list[SweepPointSchema]
    n_total: int
    target_profile: str
    target_profile_details: SweepTargetProfileSchema


@router.post("/sweep", response_model=SweepResponse)
def sweep_simulation(body: SweepRequest, db: Session = Depends(get_db)):
    blend = db.query(Blend).filter(Blend.id == body.blend_id).first()
    if not blend:
        raise HTTPException(404, detail="Blend not found")
    if not blend.ingredients:
        raise HTTPException(400, detail="Blend has no ingredients")

    application = None
    if body.application_id is not None:
        application = db.query(Application).filter(Application.id == body.application_id).first()
        if application is None:
            raise HTTPException(404, detail="Application not found")
    elif blend.application_id is not None:
        application = db.query(Application).filter(Application.id == blend.application_id).first()

    target_profile = get_sweep_target_profile(application.name if application else None)

    calc = BlendCalculator()
    props = calc.calculate(
        [(bi.ingredient, bi.proportion) for bi in blend.ingredients]
    )

    ft = SweepRange(
        min=body.fermentation_temp.min, max=body.fermentation_temp.max,
        step=body.fermentation_temp.step, n=body.fermentation_temp.n,
    )
    fd = SweepRange(
        min=body.fermentation_duration.min, max=body.fermentation_duration.max,
        step=body.fermentation_duration.step, n=body.fermentation_duration.n,
    )
    bt = SweepRange(
        min=body.baking_temp.min, max=body.baking_temp.max,
        step=body.baking_temp.step, n=body.baking_temp.n,
    )
    bd = SweepRange(
        min=body.baking_duration.min, max=body.baking_duration.max,
        step=body.baking_duration.step, n=body.baking_duration.n,
    )

    sweeper = SimulationSweeper()

    if body.strategy == "grid":
        param_points = sweeper.generate_grid(ft, fd, bt, bd)
    else:
        param_points = sweeper.generate_random(
            ft, fd, bt, bd, n_samples=body.n_samples, seed=body.seed,
        )

    result = sweeper.run_sweep(
        props, param_points,
        top_n=body.top_n,
        w_volume=body.w_volume,
        w_gelatinization=body.w_gelatinization,
        w_crust=body.w_crust,
        w_efficiency=body.w_efficiency,
        target_profile=target_profile,
    )

    return SweepResponse(
        points=[
            SweepPointSchema(
                fermentation_temp_c=p.fermentation_temp_c,
                fermentation_duration_min=p.fermentation_duration_min,
                baking_temp_c=p.baking_temp_c,
                baking_duration_min=p.baking_duration_min,
                volume_increase=p.volume_increase,
                core_temp_c=p.core_temp_c,
                crust_temp_c=p.crust_temp_c,
                composite_score=p.composite_score,
            )
            for p in result.points
        ],
        n_total=result.n_total,
        target_profile=target_profile.name,
        target_profile_details=serialize_sweep_target_profile(target_profile),
    )
