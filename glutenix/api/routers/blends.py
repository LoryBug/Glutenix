from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from glutenix.api.deps import get_db
from glutenix.db.models import Blend, BlendIngredient
from glutenix.schemas.models import BlendCreate, BlendResponse

router = APIRouter(prefix="/blends", tags=["blends"])


@router.get("", response_model=list[BlendResponse])
def list_blends(db: Session = Depends(get_db)):
    return db.query(Blend).all()


@router.get("/{blend_id}", response_model=BlendResponse)
def get_blend(blend_id: int, db: Session = Depends(get_db)):
    blend = db.query(Blend).filter(Blend.id == blend_id).first()
    if not blend:
        raise HTTPException(404, detail="Blend not found")
    return blend


@router.post("", response_model=BlendResponse, status_code=201)
def create_blend(body: BlendCreate, db: Session = Depends(get_db)):
    blend = Blend(
        name=body.name,
        description=body.description,
        application_id=body.application_id,
    )
    for ing in body.ingredients:
        blend.ingredients.append(
            BlendIngredient(ingredient_id=ing.ingredient_id, proportion=ing.proportion)
        )
    db.add(blend)
    db.commit()
    db.refresh(blend)
    return blend


@router.delete("/{blend_id}", status_code=204)
def delete_blend(blend_id: int, db: Session = Depends(get_db)):
    blend = db.query(Blend).filter(Blend.id == blend_id).first()
    if not blend:
        raise HTTPException(404, detail="Blend not found")
    db.query(BlendIngredient).filter(BlendIngredient.blend_id == blend_id).delete()
    db.delete(blend)
    db.commit()
