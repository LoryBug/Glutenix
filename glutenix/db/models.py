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
        CheckConstraint(
            "sugars_pct is null or (sugars_pct >= 0 and sugars_pct <= 100)",
            name="ck_ingredient_sugars_pct",
        ),
        CheckConstraint(
            "saturated_fat_pct is null or (saturated_fat_pct >= 0 and saturated_fat_pct <= 100)",
            name="ck_ingredient_saturated_fat_pct",
        ),
        CheckConstraint(
            "sodium_mg_per_100g is null or sodium_mg_per_100g >= 0",
            name="ck_ingredient_sodium",
        ),
        CheckConstraint(
            "kcal_per_100g is null or kcal_per_100g >= 0",
            name="ck_ingredient_kcal",
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

    kcal_per_100g: Mapped[Optional[float]] = mapped_column(Float, comment="Energy kcal per 100g")
    sugars_pct: Mapped[Optional[float]] = mapped_column(Float, comment="of which sugars")
    saturated_fat_pct: Mapped[Optional[float]] = mapped_column(Float, comment="of which saturated fat")
    sodium_mg_per_100g: Mapped[Optional[float]] = mapped_column(Float, comment="Sodium in mg per 100g")

    starch_type: Mapped[Optional[str]] = mapped_column(
        String(20), comment="rice | maize | tapioca | potato | millet | buckwheat | None (generic)"
    )

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
    simulation_runs: Mapped[list["SimulationRun"]] = relationship(
        back_populates="application",
        passive_deletes=True,
    )

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


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    __table_args__ = (
        CheckConstraint(
            "status in ('new', 'reviewed', 'archived')",
            name="ck_simulation_run_status",
        ),
        CheckConstraint("blend_samples is null or blend_samples > 0", name="ck_simulation_run_blend_samples"),
        CheckConstraint("process_samples is null or process_samples > 0", name="ck_simulation_run_process_samples"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("applications.id", ondelete="SET NULL"), index=True
    )
    application_name: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="cli")
    preset: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    seed: Mapped[Optional[int]] = mapped_column(Integer)
    blend_samples: Mapped[Optional[int]] = mapped_column(Integer)
    process_samples: Mapped[Optional[int]] = mapped_column(Integer)
    top_n: Mapped[Optional[int]] = mapped_column(Integer)
    process_bounds: Mapped[Optional[str]] = mapped_column(Text, comment="JSON process search bounds")
    parameters: Mapped[Optional[str]] = mapped_column(Text, comment="JSON run parameters")
    git_commit: Mapped[Optional[str]] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new")
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    application: Mapped[Optional["Application"]] = relationship(back_populates="simulation_runs")
    candidates: Mapped[list["SimulationCandidate"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="SimulationCandidate.rank",
    )

    def __repr__(self):
        return f"<SimulationRun {self.application_name} preset={self.preset}>"


class SimulationCandidate(Base):
    __tablename__ = "simulation_candidates"

    __table_args__ = (
        CheckConstraint(
            "status in ('new', 'promising', 'avoid', 'test_next', 'tested', 'archived')",
            name="ck_simulation_candidate_status",
        ),
        CheckConstraint("rank > 0", name="ck_simulation_candidate_rank"),
        CheckConstraint("score >= 0", name="ck_simulation_candidate_score"),
        UniqueConstraint("run_id", "rank", name="uq_simulation_candidate_run_rank"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    process_score: Mapped[Optional[float]] = mapped_column(Float)
    blend_score: Mapped[Optional[float]] = mapped_column(Float)
    flavor_score: Mapped[Optional[float]] = mapped_column(Float)
    proportions: Mapped[str] = mapped_column(Text, nullable=False, comment="JSON candidate formula")
    process: Mapped[str] = mapped_column(Text, nullable=False, comment="JSON candidate process")
    properties: Mapped[str] = mapped_column(Text, nullable=False, comment="JSON blend properties")
    metrics: Mapped[str] = mapped_column(Text, nullable=False, comment="JSON simulated metrics")
    confidence: Mapped[str] = mapped_column(Text, nullable=False, comment="JSON confidence metadata")
    risk_flags: Mapped[Optional[str]] = mapped_column(Text, comment="JSON risk flag list")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new", index=True)
    decision_notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    run: Mapped["SimulationRun"] = relationship(back_populates="candidates")

    def __repr__(self):
        return f"<SimulationCandidate run={self.run_id} rank={self.rank} status={self.status}>"


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
