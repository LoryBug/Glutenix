from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from glutenix.api.deps import get_db
from glutenix.db.models import Application, Blend, BlendIngredient, Ingredient
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
    if body.application_id is not None:
        application = db.query(Application).filter(Application.id == body.application_id).first()
        if application is None:
            raise HTTPException(404, detail="Application not found")

    ingredient_ids = [ing.ingredient_id for ing in body.ingredients]
    existing_ids = {
        row[0]
        for row in db.query(Ingredient.id).filter(Ingredient.id.in_(ingredient_ids)).all()
    }
    missing_ids = sorted(set(ingredient_ids) - existing_ids)
    if missing_ids:
        raise HTTPException(404, detail=f"Ingredients not found: {missing_ids}")

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
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, detail="Blend could not be created") from exc
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
