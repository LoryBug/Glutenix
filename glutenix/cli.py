"""Small command-line tools for Glutenix experimentation."""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import math
import random
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from glutenix.calibration.coverage import assess_literature_coverage, build_domain_coverage
from glutenix.db.base import Base
from glutenix.db.models import Ingredient
from glutenix.db.seed import _seed_applications, _seed_ingredients
from glutenix.engine.blend import BlendCalculator, BlendProperties
from glutenix.engine.bread import BreadQualityParams, BreadQualityResult, BreadQualitySimulator
from glutenix.engine.confidence import assess_candidate_confidence, serialize_candidate_confidence
from glutenix.engine.flavor import calculate_blend_flavor, get_flavor_target, score_flavor_against_target
from glutenix.engine.targets import get_sweep_target_profile, score_blend_against_profile


@dataclass(frozen=True)
class IngredientBound:
    name: str
    min_proportion: float
    max_proportion: float


@dataclass(frozen=True)
class ProcessBounds:
    fermentation_temp_c: tuple[float, float] = (30.0, 34.0)
    fermentation_duration_min: tuple[float, float] = (120.0, 180.0)
    baking_temp_c: tuple[float, float] = (200.0, 218.0)
    baking_duration_min: tuple[float, float] = (30.0, 42.0)


@dataclass(frozen=True)
class PaneRankCandidate:
    rank: int
    score: float
    process_score: float
    blend_score: float
    flavor_score: float
    proportions: dict[str, float]
    process: dict[str, float]
    properties: dict[str, float]
    bread_metrics: dict[str, Any]
    model_confidence: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "score": self.score,
            "process_score": self.process_score,
            "blend_score": self.blend_score,
            "flavor_score": self.flavor_score,
            "proportions": self.proportions,
            "process": self.process,
            "properties": self.properties,
            "bread_metrics": self.bread_metrics,
            "model_confidence": self.model_confidence,
        }


PRESETS: dict[str, list[IngredientBound]] = {
    "sorghum-baseline": [
        IngredientBound("Sorghum flour", 0.30, 0.45),
        IngredientBound("White rice flour", 0.20, 0.42),
        IngredientBound("Tapioca starch", 0.18, 0.34),
        IngredientBound("Psyllium husk", 0.012, 0.028),
        IngredientBound("HPMC (Hydroxypropyl Methylcellulose)", 0.012, 0.028),
    ],
    "bobs-inspired": [
        IngredientBound("Sorghum flour", 0.25, 0.45),
        IngredientBound("Potato starch", 0.15, 0.35),
        IngredientBound("Corn starch", 0.10, 0.25),
        IngredientBound("Pea protein powder", 0.03, 0.08),
        IngredientBound("Tapioca starch", 0.10, 0.25),
        IngredientBound("Xanthan gum", 0.005, 0.015),
        IngredientBound("Guar gum", 0.005, 0.015),
    ],
    "schaer-inspired": [
        IngredientBound("Corn starch", 0.35, 0.55),
        IngredientBound("White rice flour", 0.30, 0.50),
        IngredientBound("Brown rice flour", 0.03, 0.08),
        IngredientBound("Chickpea flour", 0.02, 0.06),
        IngredientBound("Psyllium husk", 0.010, 0.030),
        IngredientBound("HPMC (Hydroxypropyl Methylcellulose)", 0.005, 0.020),
    ],
    "freee-inspired": [
        IngredientBound("White rice flour", 0.35, 0.65),
        IngredientBound("Tapioca starch", 0.15, 0.35),
        IngredientBound("Potato starch", 0.15, 0.35),
        IngredientBound("Xanthan gum", 0.005, 0.020),
    ],
    "quinoa-hpmc": [
        IngredientBound("Quinoa flour", 0.20, 0.45),
        IngredientBound("White rice flour", 0.25, 0.55),
        IngredientBound("Tapioca starch", 0.15, 0.35),
        IngredientBound("HPMC (Hydroxypropyl Methylcellulose)", 0.010, 0.030),
    ],
}


def rank_pane_candidates(
    *,
    preset: str,
    n_blend_samples: int = 100,
    n_process_samples: int = 20,
    top: int = 10,
    seed: int | None = None,
    process_bounds: ProcessBounds = ProcessBounds(),
    db: Session | None = None,
) -> list[PaneRankCandidate]:
    if preset not in PRESETS:
        raise ValueError(f"Unknown Pane preset: {preset}")
    if n_blend_samples < 1 or n_process_samples < 1 or top < 1:
        raise ValueError("n_blend_samples, n_process_samples, and top must be positive")

    own_session = db is None
    session = db or _seeded_session()
    try:
        return _rank_pane_candidates(
            session=session,
            bounds=PRESETS[preset],
            n_blend_samples=n_blend_samples,
            n_process_samples=n_process_samples,
            top=top,
            seed=seed,
            process_bounds=process_bounds,
        )
    finally:
        if own_session:
            session.close()


def _rank_pane_candidates(
    *,
    session: Session,
    bounds: list[IngredientBound],
    n_blend_samples: int,
    n_process_samples: int,
    top: int,
    seed: int | None,
    process_bounds: ProcessBounds,
) -> list[PaneRankCandidate]:
    ingredients = _resolve_ingredients(session, bounds)
    rng = random.Random(seed)
    process_points = _sample_process_points(process_bounds, n_process_samples, rng)
    profile = get_sweep_target_profile("Pane")
    flavor_target = get_flavor_target("Pane")
    coverage_summary = build_domain_coverage(session, "bread_baking")
    calc = BlendCalculator()

    candidates = []
    attempts = 0
    while len(candidates) < n_blend_samples and attempts < n_blend_samples * 20:
        attempts += 1
        proportions = _sample_bounded_proportions(ingredients, rng, max_attempts=20)
        if proportions is None:
            break

        blend_data = [(ingredient, prop) for (ingredient, _, _), prop in zip(ingredients, proportions)]
        blend_props = calc.calculate(blend_data)
        best_bread, best_point, process_score = _best_bread_process(blend_props, process_points, profile)
        blend_values = _blend_values(blend_props)
        blend_score = score_blend_against_profile(blend_values, profile)
        flavor_profile = calculate_blend_flavor(blend_data)
        flavor_score = score_flavor_against_target(flavor_profile, flavor_target)
        total_score = 0.55 * process_score + 0.25 * blend_score + 0.20 * flavor_score
        bread_metrics = _serialize_bread_metrics(best_bread)
        literature_coverage = assess_literature_coverage(
            application="Pane",
            ingredient_names=[ingredient.name for ingredient, prop in blend_data if prop > 1e-6],
            blend_values=blend_values,
            process_values=best_point,
            summary=coverage_summary,
        ).as_dict()
        confidence = serialize_candidate_confidence(assess_candidate_confidence(
            blend_values=blend_values,
            profile=profile,
            process_score=process_score,
            blend_score=blend_score,
            flavor_score=flavor_score,
            bread_metrics=bread_metrics,
            literature_coverage=literature_coverage,
        ))
        candidates.append((
            total_score,
            process_score,
            blend_score,
            flavor_score,
            {ingredient.name: prop for (ingredient, _, _), prop in zip(ingredients, proportions)},
            best_point,
            blend_values,
            bread_metrics,
            confidence,
        ))

    candidates.sort(key=lambda item: item[0], reverse=True)
    return [
        PaneRankCandidate(
            rank=rank,
            score=round(total_score, 4),
            process_score=round(process_score, 4),
            blend_score=round(blend_score, 4),
            flavor_score=round(flavor_score, 4),
            proportions={name: round(value, 4) for name, value in proportions.items()},
            process={key: round(value, 4) for key, value in process.items()},
            properties={key: round(value, 4) for key, value in properties.items()},
            bread_metrics=bread_metrics,
            model_confidence=confidence,
        )
        for rank, (
            total_score,
            process_score,
            blend_score,
            flavor_score,
            proportions,
            process,
            properties,
            bread_metrics,
            confidence,
        ) in enumerate(candidates[:top], start=1)
    ]


def _seeded_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session = Session(bind=engine.connect())
    with contextlib.redirect_stdout(io.StringIO()):
        _seed_ingredients(session)
        _seed_applications(session)
    session.commit()
    return session


def _resolve_ingredients(
    session: Session,
    bounds: list[IngredientBound],
) -> list[tuple[Ingredient, float, float]]:
    by_name = {ingredient.name: ingredient for ingredient in session.query(Ingredient).all()}
    items = []
    for bound in bounds:
        ingredient = by_name.get(bound.name)
        if ingredient is None:
            raise ValueError(f"Ingredient not found in seed data: {bound.name}")
        if bound.min_proportion < 0 or bound.max_proportion < bound.min_proportion:
            raise ValueError(f"Invalid proportion bounds for {bound.name}")
        items.append((ingredient, bound.min_proportion, bound.max_proportion))
    return items


def _sample_bounded_proportions(
    items: list[tuple[Ingredient, float, float]],
    rng: random.Random,
    max_attempts: int,
) -> list[float] | None:
    min_sum = sum(lo for _, lo, _ in items)
    max_sum = sum(hi for _, _, hi in items)
    if min_sum > 1.0 or max_sum < 1.0:
        return None

    for _ in range(max_attempts):
        props = [lo for _, lo, _ in items]
        caps = [hi - lo for _, lo, hi in items]
        remaining = 1.0 - min_sum
        order = list(range(len(items)))
        rng.shuffle(order)

        for pos, idx in enumerate(order[:-1]):
            rest = order[pos + 1:]
            rest_capacity = sum(caps[j] for j in rest)
            min_add = max(0.0, remaining - rest_capacity)
            max_add = min(caps[idx], remaining)
            if min_add > max_add + 1e-12:
                break
            add = rng.uniform(min_add, max_add)
            props[idx] += add
            remaining -= add
        else:
            last = order[-1]
            if remaining <= caps[last] + 1e-9:
                props[last] += remaining
                return props
    return None


def _sample_process_points(
    bounds: ProcessBounds,
    n_samples: int,
    rng: random.Random,
) -> list[dict[str, float]]:
    return [
        {
            "fermentation_temp_c": rng.uniform(*bounds.fermentation_temp_c),
            "fermentation_duration_min": rng.uniform(*bounds.fermentation_duration_min),
            "baking_temp_c": rng.uniform(*bounds.baking_temp_c),
            "baking_duration_min": rng.uniform(*bounds.baking_duration_min),
        }
        for _ in range(n_samples)
    ]


def _best_bread_process(
    blend_props: BlendProperties,
    process_points: list[dict[str, float]],
    profile,
) -> tuple[BreadQualityResult, dict[str, float], float]:
    best_bread = None
    best_point = None
    best_score = -1.0
    for point in process_points:
        bread = BreadQualitySimulator(BreadQualityParams(
            fermentation_temp_c=point["fermentation_temp_c"],
            fermentation_time_min=point["fermentation_duration_min"],
            baking_temp_c=point["baking_temp_c"],
            baking_time_min=point["baking_duration_min"],
        )).simulate(blend_props)
        score = _score_bread_quality(bread, profile)
        if best_bread is None or score > best_score:
            best_bread = bread
            best_point = point
            best_score = score
    if best_bread is None or best_point is None:
        raise ValueError("No process points were generated")
    return best_bread, best_point, best_score


def _score_bread_quality(result: BreadQualityResult, profile) -> float:
    volume_score = math.exp(-0.5 * ((result.specific_volume_cm3_g - 2.5) / 0.6) ** 2)
    core_target = profile.core_target_c or 96.0
    core_score = math.exp(-0.5 * ((result.core_temp_c - core_target) / profile.core_sigma_c) ** 2)
    crust_score = math.exp(-0.5 * ((result.crust_temp_c - profile.crust_target_c) / profile.crust_sigma_c) ** 2)
    return float(0.45 * volume_score + 0.35 * core_score + 0.20 * crust_score)


def _blend_values(props: BlendProperties) -> dict[str, float]:
    return {
        "protein_pct": props.protein_pct,
        "starch_pct": props.starch_pct,
        "fat_pct": props.fat_pct,
        "fiber_pct": props.fiber_pct,
        "water_absorption": props.water_absorption,
        "viscosity_index": props.viscosity_index,
        "hydrocolloid_pct": props.hydrocolloid_pct,
        "amylose_pct": props.amylose_pct,
    }


def _serialize_bread_metrics(result: BreadQualityResult) -> dict[str, Any]:
    return {
        "specific_volume_cm3_g": result.specific_volume_cm3_g,
        "crumb_hardness_n": result.crumb_hardness_n,
        "porosity_pct": result.porosity_pct,
        "process_family": result.process_family,
        "calibration_confidence": result.calibration_confidence,
        "calibration_score": result.calibration_score,
        "calibration_notes": result.calibration_notes,
    }


def _print_candidates(candidates: list[PaneRankCandidate]) -> None:
    print("rank score conf vol_cm3_g hard_N protein viscosity top_risk")
    for candidate in candidates:
        confidence = candidate.model_confidence
        bread = candidate.bread_metrics
        properties = candidate.properties
        risks = confidence.get("risk_flags", [])
        top_risk = risks[0] if risks else "none"
        print(
            f"{candidate.rank:>4} "
            f"{candidate.score:>5.3f} "
            f"{confidence['level']:<6} "
            f"{bread['specific_volume_cm3_g']:>8.3f} "
            f"{bread['crumb_hardness_n']:>6.2f} "
            f"{properties['protein_pct']:>7.2f} "
            f"{properties['viscosity_index']:>9.3f} "
            f"{top_risk}"
        )


def _write_json(path: Path, candidates: list[PaneRankCandidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([candidate.as_dict() for candidate in candidates], indent=2),
        encoding="utf-8",
    )


def _write_csv(path: Path, candidates: list[PaneRankCandidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "rank",
            "score",
            "confidence_level",
            "confidence_score",
            "specific_volume_cm3_g",
            "crumb_hardness_n",
            "porosity_pct",
            "protein_pct",
            "viscosity_index",
            "hydrocolloid_pct",
            "fermentation_temp_c",
            "fermentation_duration_min",
            "baking_temp_c",
            "baking_duration_min",
            "proportions_json",
            "top_risk",
        ])
        writer.writeheader()
        for candidate in candidates:
            risks = candidate.model_confidence.get("risk_flags", [])
            writer.writerow({
                "rank": candidate.rank,
                "score": candidate.score,
                "confidence_level": candidate.model_confidence["level"],
                "confidence_score": candidate.model_confidence["score"],
                "specific_volume_cm3_g": candidate.bread_metrics["specific_volume_cm3_g"],
                "crumb_hardness_n": candidate.bread_metrics["crumb_hardness_n"],
                "porosity_pct": candidate.bread_metrics["porosity_pct"],
                "protein_pct": candidate.properties["protein_pct"],
                "viscosity_index": candidate.properties["viscosity_index"],
                "hydrocolloid_pct": candidate.properties["hydrocolloid_pct"],
                "fermentation_temp_c": candidate.process["fermentation_temp_c"],
                "fermentation_duration_min": candidate.process["fermentation_duration_min"],
                "baking_temp_c": candidate.process["baking_temp_c"],
                "baking_duration_min": candidate.process["baking_duration_min"],
                "proportions_json": json.dumps(candidate.proportions, sort_keys=True),
                "top_risk": risks[0] if risks else "",
            })


def _rank_pane_command(args: argparse.Namespace) -> int:
    candidates = rank_pane_candidates(
        preset=args.preset,
        n_blend_samples=args.blend_samples,
        n_process_samples=args.process_samples,
        top=args.top,
        seed=args.seed,
    )
    _print_candidates(candidates)
    if args.json:
        _write_json(Path(args.json), candidates)
        print(f"JSON written to {args.json}")
    if args.csv:
        _write_csv(Path(args.csv), candidates)
        print(f"CSV written to {args.csv}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    rank_pane = subparsers.add_parser(
        "rank-pane",
        help="Rank Pane blend candidates without starting the API.",
    )
    rank_pane.add_argument("--preset", choices=sorted(PRESETS), default="sorghum-baseline")
    rank_pane.add_argument("--blend-samples", type=int, default=100)
    rank_pane.add_argument("--process-samples", type=int, default=20)
    rank_pane.add_argument("--top", type=int, default=10)
    rank_pane.add_argument("--seed", type=int, default=None)
    rank_pane.add_argument("--json", help="Optional JSON output path.")
    rank_pane.add_argument("--csv", help="Optional CSV output path.")
    rank_pane.set_defaults(func=_rank_pane_command)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
