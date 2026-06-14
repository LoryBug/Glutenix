from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from glutenix.db.base import Base


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="flour | starch | hydrocolloid"
    )
    scientific_name: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)

    protein_pct: Mapped[Optional[float]] = mapped_column(Float)
    starch_pct: Mapped[Optional[float]] = mapped_column(Float)
    fat_pct: Mapped[Optional[float]] = mapped_column(Float)
    fiber_pct: Mapped[Optional[float]] = mapped_column(Float)
    moisture_pct: Mapped[Optional[float]] = mapped_column(Float)
    ash_pct: Mapped[Optional[float]] = mapped_column(Float)

    water_absorption: Mapped[Optional[float]] = mapped_column(
        Float, comment="g water per g flour"
    )
    gelatinization_temp_min: Mapped[Optional[float]] = mapped_column(Float)
    gelatinization_temp_max: Mapped[Optional[float]] = mapped_column(Float)
    amylose_pct: Mapped[Optional[float]] = mapped_column(Float)

    extra_properties: Mapped[Optional[str]] = mapped_column(
        Text, comment="JSON for uncommon properties"
    )

    blends: Mapped[list["BlendIngredient"]] = relationship(back_populates="ingredient")

    def __repr__(self):
        return f"<Ingredient {self.name} ({self.category})>"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    target_properties: Mapped[Optional[str]] = mapped_column(
        Text, comment="JSON target ranges for key metrics"
    )

    blends: Mapped[list["Blend"]] = relationship(back_populates="application")

    def __repr__(self):
        return f"<Application {self.name}>"


class Blend(Base):
    __tablename__ = "blends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    application_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("applications.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )

    application: Mapped[Optional["Application"]] = relationship(
        back_populates="blends"
    )
    ingredients: Mapped[list["BlendIngredient"]] = relationship(
        back_populates="blend", cascade="all, delete-orphan"
    )
    simulation_results: Mapped[list["SimulationResult"]] = relationship(
        back_populates="blend", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Blend {self.name}>"


class BlendIngredient(Base):
    __tablename__ = "blend_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    blend_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("blends.id"), nullable=False
    )
    ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredients.id"), nullable=False
    )
    proportion: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Fraction of total blend (0-1)"
    )

    blend: Mapped["Blend"] = relationship(back_populates="ingredients")
    ingredient: Mapped["Ingredient"] = relationship(back_populates="blends")

    def __repr__(self):
        return f"<BlendIngredient {self.ingredient_id}: {self.proportion:.2%}>"


class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    blend_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("blends.id"), nullable=False
    )
    application_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("applications.id")
    )
    parameters: Mapped[Optional[str]] = mapped_column(
        Text, comment="JSON simulation parameters"
    )
    results: Mapped[str] = mapped_column(
        Text, nullable=False, comment="JSON simulation output"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )

    blend: Mapped["Blend"] = relationship(back_populates="simulation_results")

    def __repr__(self):
        return f"<SimulationResult blend={self.blend_id}>"


class ExperimentResult(Base):
    __tablename__ = "experiment_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    blend_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("blends.id"), nullable=False
    )
    application_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("applications.id")
    )
    conditions: Mapped[Optional[str]] = mapped_column(
        Text, comment="JSON experimental conditions (temp, humidity, time)"
    )
    metrics: Mapped[str] = mapped_column(
        Text, nullable=False, comment="JSON measured metrics"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )

    def __repr__(self):
        return f"<ExperimentResult blend={self.blend_id}>"
