from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from glutenix.db.base import Base


class Ingredient(Base):
    __tablename__ = "ingredients"

    __table_args__ = (
        CheckConstraint("category in ('flour', 'starch', 'hydrocolloid')", name="ck_ingredient_category"),
        CheckConstraint(
            "protein_pct is null or (protein_pct >= 0 and protein_pct <= 100)",
            name="ck_ingredient_protein_pct",
        ),
        CheckConstraint(
            "starch_pct is null or (starch_pct >= 0 and starch_pct <= 100)",
            name="ck_ingredient_starch_pct",
        ),
        CheckConstraint(
            "fat_pct is null or (fat_pct >= 0 and fat_pct <= 100)",
            name="ck_ingredient_fat_pct",
        ),
        CheckConstraint(
            "fiber_pct is null or (fiber_pct >= 0 and fiber_pct <= 100)",
            name="ck_ingredient_fiber_pct",
        ),
        CheckConstraint(
            "moisture_pct is null or (moisture_pct >= 0 and moisture_pct <= 100)",
            name="ck_ingredient_moisture_pct",
        ),
        CheckConstraint(
            "ash_pct is null or (ash_pct >= 0 and ash_pct <= 100)",
            name="ck_ingredient_ash_pct",
        ),
        CheckConstraint(
            "amylose_pct is null or (amylose_pct >= 0 and amylose_pct <= 100)",
            name="ck_ingredient_amylose_pct",
        ),
    )

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

    blends: Mapped[list["BlendIngredient"]] = relationship(
        back_populates="ingredient",
        passive_deletes=True,
    )

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
        Integer, ForeignKey("applications.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
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
    experiment_results: Mapped[list["ExperimentResult"]] = relationship(
        back_populates="blend", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Blend {self.name}>"


class BlendIngredient(Base):
    __tablename__ = "blend_ingredients"

    __table_args__ = (
        CheckConstraint(
            "proportion > 0 and proportion <= 1",
            name="ck_blend_ingredient_proportion",
        ),
        UniqueConstraint("blend_id", "ingredient_id", name="uq_blend_ingredient"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    blend_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("blends.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False, index=True
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
        Integer, ForeignKey("blends.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("applications.id", ondelete="SET NULL"), index=True
    )
    parameters: Mapped[Optional[str]] = mapped_column(
        Text, comment="JSON simulation parameters"
    )
    results: Mapped[str] = mapped_column(
        Text, nullable=False, comment="JSON simulation output"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    blend: Mapped["Blend"] = relationship(back_populates="simulation_results")
    application: Mapped[Optional["Application"]] = relationship()

    def __repr__(self):
        return f"<SimulationResult blend={self.blend_id}>"


class ExperimentResult(Base):
    __tablename__ = "experiment_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    blend_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("blends.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("applications.id", ondelete="SET NULL"), index=True
    )
    conditions: Mapped[Optional[str]] = mapped_column(
        Text, comment="JSON experimental conditions (temp, humidity, time)"
    )
    metrics: Mapped[str] = mapped_column(
        Text, nullable=False, comment="JSON measured metrics"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    blend: Mapped["Blend"] = relationship(back_populates="experiment_results")
    application: Mapped[Optional["Application"]] = relationship()

    def __repr__(self):
        return f"<ExperimentResult blend={self.blend_id}>"
