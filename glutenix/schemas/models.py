from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class IngredientCreate(BaseModel):
    name: str = Field(max_length=100)
    category: str = Field(
        max_length=20, pattern=r"^(flour|starch|hydrocolloid)$"
    )
    scientific_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None

    protein_pct: Optional[float] = Field(None, ge=0, le=100)
    starch_pct: Optional[float] = Field(None, ge=0, le=100)
    fat_pct: Optional[float] = Field(None, ge=0, le=100)
    fiber_pct: Optional[float] = Field(None, ge=0, le=100)
    moisture_pct: Optional[float] = Field(None, ge=0, le=100)
    ash_pct: Optional[float] = Field(None, ge=0, le=100)

    water_absorption: Optional[float] = Field(None, ge=0)
    gelatinization_temp_min: Optional[float] = Field(None, ge=0)
    gelatinization_temp_max: Optional[float] = Field(None, ge=0)
    amylose_pct: Optional[float] = Field(None, ge=0, le=100)

    extra_properties: Optional[str] = None


class IngredientResponse(IngredientCreate):
    id: int

    model_config = {"from_attributes": True}


class ApplicationCreate(BaseModel):
    name: str = Field(max_length=50)
    description: Optional[str] = None
    target_properties: Optional[str] = None


class ApplicationResponse(ApplicationCreate):
    id: int

    model_config = {"from_attributes": True}


class BlendIngredientCreate(BaseModel):
    ingredient_id: int
    proportion: float = Field(gt=0, le=1)


class BlendCreate(BaseModel):
    name: str = Field(max_length=100)
    description: Optional[str] = None
    application_id: Optional[int] = None
    ingredients: list[BlendIngredientCreate]


class BlendIngredientResponse(BlendIngredientCreate):
    id: int
    blend_id: int

    model_config = {"from_attributes": True}


class BlendResponse(BlendCreate):
    id: int
    created_at: datetime
    ingredients: list[BlendIngredientResponse]

    model_config = {"from_attributes": True}


class SimulationResultCreate(BaseModel):
    blend_id: int
    application_id: Optional[int] = None
    parameters: Optional[str] = None
    results: str


class SimulationResultResponse(SimulationResultCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ExperimentResultCreate(BaseModel):
    blend_id: int
    application_id: Optional[int] = None
    conditions: Optional[str] = None
    metrics: str


class ExperimentResultResponse(ExperimentResultCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
