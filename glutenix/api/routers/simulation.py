from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from glutenix.api.deps import get_db
from glutenix.db.models import Blend, SimulationResult
from glutenix.engine.baking import BakingParams, BakingSimulator
from glutenix.engine.blend import BlendCalculator
from glutenix.engine.fermentation import FermentationParams, FermentationSimulator

router = APIRouter(prefix="/simulate", tags=["simulation"])


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
