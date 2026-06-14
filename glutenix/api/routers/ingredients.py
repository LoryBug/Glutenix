from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from glutenix.api.deps import get_db
from glutenix.db.models import Ingredient
from glutenix.schemas.models import IngredientCreate, IngredientResponse

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


@router.get("", response_model=list[IngredientResponse])
def list_ingredients(db: Session = Depends(get_db)):
    return db.query(Ingredient).all()


@router.get("/{ingredient_id}", response_model=IngredientResponse)
def get_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    ing = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ing:
        raise HTTPException(404, detail="Ingredient not found")
    return ing


@router.post("", response_model=IngredientResponse, status_code=201)
def create_ingredient(body: IngredientCreate, db: Session = Depends(get_db)):
    ing = Ingredient(**body.model_dump())
    db.add(ing)
    db.commit()
    db.refresh(ing)
    return ing


@router.put("/{ingredient_id}", response_model=IngredientResponse)
def update_ingredient(ingredient_id: int, body: IngredientCreate, db: Session = Depends(get_db)):
    ing = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ing:
        raise HTTPException(404, detail="Ingredient not found")
    for key, val in body.model_dump().items():
        setattr(ing, key, val)
    db.commit()
    db.refresh(ing)
    return ing


@router.delete("/{ingredient_id}", status_code=204)
def delete_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    ing = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ing:
        raise HTTPException(404, detail="Ingredient not found")
    db.delete(ing)
    db.commit()
