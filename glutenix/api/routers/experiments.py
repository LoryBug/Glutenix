from datetime import datetime, timezone
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from glutenix.api.deps import get_db
from glutenix.db.models import Blend, ExperimentResult

router = APIRouter(prefix="/experiments", tags=["experiments"])


class ExperimentCreate(BaseModel):
    blend_id: int = Field(gt=0)
    conditions: str = Field(default="{}", description="JSON: temp, umidità, tempo lievitazione/cottura")
    metrics: str = Field(description="JSON: volume, core_temp, crust_temp, texture_score, ecc.")

    @field_validator("conditions", "metrics")
    @classmethod
    def valid_json(cls, value: str) -> str:
        json.loads(value)
        return value


class ExperimentResponse(BaseModel):
    id: int
    blend_id: int
    conditions: str | None
    metrics: str
    created_at: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[ExperimentResponse])
def list_experiments(db: Session = Depends(get_db)):
    results = db.query(ExperimentResult).order_by(ExperimentResult.created_at.desc()).all()
    return [
        ExperimentResponse(
            id=r.id,
            blend_id=r.blend_id,
            conditions=r.conditions,
            metrics=r.metrics,
            created_at=r.created_at.isoformat(),
        )
        for r in results
    ]


@router.get("/{experiment_id}", response_model=ExperimentResponse)
def get_experiment(experiment_id: int, db: Session = Depends(get_db)):
    r = db.query(ExperimentResult).filter(ExperimentResult.id == experiment_id).first()
    if not r:
        raise HTTPException(404, detail="Experiment not found")
    return ExperimentResponse(
        id=r.id,
        blend_id=r.blend_id,
        conditions=r.conditions,
        metrics=r.metrics,
        created_at=r.created_at.isoformat(),
    )


@router.post("", response_model=ExperimentResponse, status_code=201)
def create_experiment(body: ExperimentCreate, db: Session = Depends(get_db)):
    blend = db.query(Blend).filter(Blend.id == body.blend_id).first()
    if blend is None:
        raise HTTPException(404, detail="Blend not found")

    r = ExperimentResult(
        blend_id=body.blend_id,
        conditions=body.conditions,
        metrics=body.metrics,
    )
    db.add(r)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, detail="Experiment could not be created") from exc
    db.refresh(r)
    return ExperimentResponse(
        id=r.id,
        blend_id=r.blend_id,
        conditions=r.conditions,
        metrics=r.metrics,
        created_at=r.created_at.isoformat(),
    )


@router.delete("/{experiment_id}", status_code=204)
def delete_experiment(experiment_id: int, db: Session = Depends(get_db)):
    r = db.query(ExperimentResult).filter(ExperimentResult.id == experiment_id).first()
    if not r:
        raise HTTPException(404, detail="Experiment not found")
    db.delete(r)
    db.commit()
