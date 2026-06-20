from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


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

    kcal_per_100g: Optional[float] = Field(None, ge=0)
    sugars_pct: Optional[float] = Field(None, ge=0, le=100)
    saturated_fat_pct: Optional[float] = Field(None, ge=0, le=100)
    sodium_mg_per_100g: Optional[float] = Field(None, ge=0)

    starch_type: Optional[str] = Field(
        None, max_length=20, pattern=r"^(rice|maize|tapioca|potato|millet|buckwheat)?$"
    )

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
    ingredient_id: int = Field(gt=0)
    proportion: float = Field(gt=0, le=1)


class BlendCreate(BaseModel):
    name: str = Field(max_length=100)
    description: Optional[str] = None
    application_id: Optional[int] = Field(None, gt=0)
    ingredients: list[BlendIngredientCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def proportions_sum_to_one(self):
        total = sum(i.proportion for i in self.ingredients)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Proportions must sum to 1, got {total}")
        ids = [i.ingredient_id for i in self.ingredients]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate ingredient_id values are not allowed")
        return self


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
    blend_id: int = Field(gt=0)
    application_id: Optional[int] = Field(None, gt=0)
    parameters: Optional[str] = None
    results: str

    @field_validator("results")
    @classmethod
    def valid_results_json(cls, value: str) -> str:
        import json
        json.loads(value)
        return value

    @field_validator("parameters")
    @classmethod
    def valid_parameters_json(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            import json
            json.loads(value)
        return value


class SimulationResultResponse(SimulationResultCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ExperimentResultCreate(BaseModel):
    blend_id: int = Field(gt=0)
    application_id: Optional[int] = Field(None, gt=0)
    conditions: Optional[str] = None
    metrics: str

    @field_validator("metrics")
    @classmethod
    def valid_metrics_json(cls, value: str) -> str:
        import json
        json.loads(value)
        return value

    @field_validator("conditions")
    @classmethod
    def valid_conditions_json(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            import json
            json.loads(value)
        return value


class ExperimentResultResponse(ExperimentResultCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
