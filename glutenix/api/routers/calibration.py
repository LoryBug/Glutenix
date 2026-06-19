from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from glutenix.api.deps import get_db
from glutenix.calibration.literature import compare_bread_baking_records, compare_pasta_cooking_records

router = APIRouter(prefix="/calibration", tags=["calibration"])


@router.get("/pasta-cooking")
def pasta_cooking_calibration(db: Session = Depends(get_db)) -> dict[str, Any]:
    return compare_pasta_cooking_records(db)


@router.get("/bread-baking")
def bread_baking_calibration(db: Session = Depends(get_db)) -> dict[str, Any]:
    return compare_bread_baking_records(db)
