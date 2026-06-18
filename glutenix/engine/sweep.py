from dataclasses import dataclass, field
from itertools import product

import numpy as np
import structlog

from glutenix.engine.baking import BakingParams, BakingSimulator
from glutenix.engine.blend import BlendProperties
from glutenix.engine.fermentation import FermentationParams, FermentationSimulator
from glutenix.engine.targets import DEFAULT_SWEEP_PROFILE, SweepTargetProfile

logger = structlog.get_logger("glutenix.engine.sweep")


@dataclass
class SweepRange:
    min: float
    max: float
    step: float | None = None
    n: int | None = None


@dataclass
class SweepPoint:
    fermentation_temp_c: float
    fermentation_duration_min: float
    baking_temp_c: float
    baking_duration_min: float
    volume_increase: float
    core_temp_c: float
    crust_temp_c: float
    composite_score: float


@dataclass
class SweepResult:
    points: list[SweepPoint] = field(default_factory=list)
    n_total: int = 0


class SimulationSweeper:
    def __init__(self, logger=logger):
        self.logger = logger

    def generate_grid(
        self,
        fermentation_temp: SweepRange,
        fermentation_duration: SweepRange,
        baking_temp: SweepRange,
        baking_duration: SweepRange,
    ) -> list[dict]:
        temps_f = np.arange(
            fermentation_temp.min, fermentation_temp.max + 1e-9,
            fermentation_temp.step or 1.0
        )
        durs_f = np.arange(
            fermentation_duration.min, fermentation_duration.max + 1e-9,
            fermentation_duration.step or 10.0
        )
        temps_b = np.arange(
            baking_temp.min, baking_temp.max + 1e-9,
            baking_temp.step or 10.0
        )
        durs_b = np.arange(
            baking_duration.min, baking_duration.max + 1e-9,
            baking_duration.step or 5.0
        )
        points = []
        for ft, fd, bt, bd in product(temps_f, durs_f, temps_b, durs_b):
            points.append({
                "fermentation_temp_c": round(float(ft), 1),
                "fermentation_duration_min": round(float(fd), 1),
                "baking_temp_c": round(float(bt), 1),
                "baking_duration_min": round(float(bd), 1),
            })
        self.logger.info("sweep_grid_generated", n_points=len(points))
        return points

    def generate_random(
        self,
        fermentation_temp: SweepRange,
        fermentation_duration: SweepRange,
        baking_temp: SweepRange,
        baking_duration: SweepRange,
        n_samples: int = 200,
        seed: int | None = None,
    ) -> list[dict]:
        rng = np.random.default_rng(seed)
        points = []
        for _ in range(n_samples):
            points.append({
                "fermentation_temp_c": round(
                    float(rng.uniform(fermentation_temp.min, fermentation_temp.max)), 1
                ),
                "fermentation_duration_min": round(
                    float(rng.uniform(fermentation_duration.min, fermentation_duration.max)), 1
                ),
                "baking_temp_c": round(
                    float(rng.uniform(baking_temp.min, baking_temp.max)), 1
                ),
                "baking_duration_min": round(
                    float(rng.uniform(baking_duration.min, baking_duration.max)), 1
                ),
            })
        self.logger.info("sweep_random_generated", n_points=len(points))
        return points

    @staticmethod
    def _compute_composite_score(
        volume_increase: float,
        core_temp_c: float,
        crust_temp_c: float,
        blend_props: BlendProperties | None = None,
        fermentation_duration_min: float | None = None,
        baking_duration_min: float | None = None,
        target_profile: SweepTargetProfile | None = None,
        w_volume: float = 0.30,
        w_gelatinization: float = 0.40,
        w_crust: float = 0.20,
        w_efficiency: float = 0.10,
    ) -> float:
        profile = target_profile or DEFAULT_SWEEP_PROFILE
        vol_score = float(
            np.exp(-0.5 * ((volume_increase - profile.volume_target) / profile.volume_sigma) ** 2)
        )

        if profile.core_target_c is not None:
            core_target = profile.core_target_c
        elif blend_props is not None:
            gel_high = blend_props.gelatinization_temp_max
            core_target = min(96.0, gel_high + profile.core_offset_from_gel_max_c)
        else:
            core_target = 90.0

        gel_score = float(
            np.exp(-0.5 * ((core_temp_c - core_target) / profile.core_sigma_c) ** 2)
        )
        crust_score = float(
            np.exp(-0.5 * ((crust_temp_c - profile.crust_target_c) / profile.crust_sigma_c) ** 2)
        )

        efficiency_score = 1.0
        if fermentation_duration_min is not None and baking_duration_min is not None:
            total_time = fermentation_duration_min + baking_duration_min
            efficiency_score = float(
                np.clip(
                    1.0 - max(0.0, total_time - profile.efficiency_start_min) / profile.efficiency_window_min,
                    0,
                    1,
                )
            )

        return float(
            w_volume * vol_score
            + w_gelatinization * gel_score
            + w_crust * crust_score
            + w_efficiency * efficiency_score
        )

    def run_sweep(
        self,
        blend_props: BlendProperties,
        param_points: list[dict],
        top_n: int = 10,
        w_volume: float = 0.30,
        w_gelatinization: float = 0.40,
        w_crust: float = 0.20,
        w_efficiency: float = 0.10,
        target_profile: SweepTargetProfile | None = None,
    ) -> SweepResult:
        results: list[SweepPoint] = []
        n_total = len(param_points)

        self.logger.info(
            "sweep_starting",
            n_points=n_total,
            top_n=top_n,
            w_volume=w_volume,
            w_gelatinization=w_gelatinization,
            w_crust=w_crust,
            w_efficiency=w_efficiency,
            target_profile=(target_profile or DEFAULT_SWEEP_PROFILE).name,
        )

        for i, pt in enumerate(param_points):
            try:
                fermenter = FermentationSimulator(
                    FermentationParams(temp_c=pt["fermentation_temp_c"])
                )
                ferm_result = fermenter.simulate(
                    viscosity_index=blend_props.viscosity_index,
                    duration_min=pt["fermentation_duration_min"],
                )

                baker = BakingSimulator(
                    BakingParams(
                        oven_temp_c=pt["baking_temp_c"],
                        baking_time_min=pt["baking_duration_min"],
                    )
                )
                bake_result = baker.simulate(
                    gelatinization_temp_min=blend_props.gelatinization_temp_min,
                    gelatinization_temp_max=blend_props.gelatinization_temp_max,
                )

                vol_inc = float(ferm_result.final_volume_increase)
                core = float(bake_result.core_temp_c)
                crust = float(bake_result.crust_temp_c)

                score = self._compute_composite_score(
                    vol_inc, core, crust, blend_props,
                    fermentation_duration_min=pt["fermentation_duration_min"],
                    baking_duration_min=pt["baking_duration_min"],
                    target_profile=target_profile,
                    w_volume=w_volume,
                    w_gelatinization=w_gelatinization,
                    w_crust=w_crust,
                    w_efficiency=w_efficiency,
                )

                results.append(SweepPoint(
                    fermentation_temp_c=pt["fermentation_temp_c"],
                    fermentation_duration_min=pt["fermentation_duration_min"],
                    baking_temp_c=pt["baking_temp_c"],
                    baking_duration_min=pt["baking_duration_min"],
                    volume_increase=round(vol_inc, 4),
                    core_temp_c=round(core, 2),
                    crust_temp_c=round(crust, 2),
                    composite_score=round(score, 4),
                ))
            except Exception as e:
                self.logger.warning(
                    "sweep_point_failed",
                    index=i,
                    point=pt,
                    error=str(e),
                )

        if not results:
            return SweepResult(points=[], n_total=n_total)

        results.sort(key=lambda p: p.composite_score, reverse=True)
        top = results[:top_n]

        self.logger.info(
            "sweep_complete",
            n_success=len(results),
            n_failed=n_total - len(results),
            top_score=top[0].composite_score if top else None,
        )

        return SweepResult(points=top, n_total=n_total)
