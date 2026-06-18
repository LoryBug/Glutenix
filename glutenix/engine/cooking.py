from dataclasses import dataclass

import numpy as np

from glutenix.engine.blend import BlendProperties


@dataclass
class PastaCookingParams:
    water_temp_c: float = 98.0
    cooking_time_min: float = 6.0
    pasta_thickness_mm: float = 2.0
    initial_temp_c: float = 20.0


@dataclass
class PastaCookingResult:
    core_temp_c: float
    water_uptake_pct: float
    cooking_loss_pct: float
    firmness_index: float
    stickiness_index: float
    quality_score: float


class PastaCookingSimulator:
    def __init__(self, params: PastaCookingParams | None = None):
        self.params = params or PastaCookingParams()

    @staticmethod
    def _ingredient_fraction(blend_props: BlendProperties, token: str) -> float:
        token = token.lower()
        return sum(
            item["proportion"]
            for item in blend_props.ingredients_detail
            if token in item["name"].lower()
        )

    def simulate(self, blend_props: BlendProperties) -> PastaCookingResult:
        p = self.params
        if p.water_temp_c <= p.initial_temp_c:
            raise ValueError("water_temp_c must be greater than initial_temp_c")
        if p.cooking_time_min <= 0:
            raise ValueError("cooking_time_min must be positive")
        if p.pasta_thickness_mm <= 0:
            raise ValueError("pasta_thickness_mm must be positive")

        temp_factor = float(np.clip((p.water_temp_c - 60.0) / 38.0, 0.05, 1.25))
        thickness_factor = max(p.pasta_thickness_mm / 2.0, 0.25)
        time_factor = p.cooking_time_min / thickness_factor

        core_temp = p.initial_temp_c + (p.water_temp_c - p.initial_temp_c) * (
            1.0 - np.exp(-0.55 * p.cooking_time_min / (thickness_factor**2))
        )

        hydrocolloid = blend_props.hydrocolloid_pct
        alginate = self._ingredient_fraction(blend_props, "alginate")
        protein = blend_props.protein_pct
        amylose = blend_props.amylose_pct
        water_absorption = blend_props.water_absorption

        structure = float(np.clip(
            0.28 * protein / 12.0
            + 0.28 * amylose / 28.0
            + 0.24 * hydrocolloid / 0.025
            + 0.20 * alginate / 0.015,
            0.0,
            1.8,
        ))
        alginate_gel = float(np.clip(alginate / 0.015, 0.0, 1.5))

        max_uptake = float(np.clip(45.0 + 35.0 * water_absorption, 55.0, 130.0))
        hydration_rate = 0.32 * temp_factor / thickness_factor
        water_uptake = max_uptake * (1.0 - np.exp(-hydration_rate * p.cooking_time_min))

        optimal_time = 5.5 * thickness_factor / temp_factor
        undercook = max(0.0, (optimal_time - p.cooking_time_min) / optimal_time)
        overcook = max(0.0, (p.cooking_time_min - optimal_time) / optimal_time)

        loss = (
            7.5
            - 3.0 * structure
            - 3.8 * alginate_gel
            + 2.5 * overcook
            + 1.2 * max(0.0, water_uptake - 85.0) / 45.0
            + 0.8 * blend_props.starch_pct / 85.0
        )
        cooking_loss = float(np.clip(loss, 0.5, 18.0))

        firmness = float(np.clip(
            0.72
            + 0.18 * structure
            - 0.42 * overcook
            + 0.22 * undercook,
            0.0,
            1.0,
        ))
        stickiness = float(np.clip(
            0.18
            + 0.055 * cooking_loss
            + 0.25 * overcook
            - 0.12 * hydrocolloid / 0.025
            - 0.18 * alginate_gel,
            0.0,
            1.0,
        ))

        loss_score = np.exp(-0.5 * (cooking_loss / 6.0) ** 2)
        uptake_score = np.exp(-0.5 * ((water_uptake - 75.0) / 28.0) ** 2)
        firmness_score = np.exp(-0.5 * ((firmness - 0.72) / 0.22) ** 2)
        stickiness_score = 1.0 - stickiness
        temp_score = np.exp(-0.5 * ((core_temp - 82.0) / 12.0) ** 2)
        quality = float(
            0.30 * loss_score
            + 0.20 * uptake_score
            + 0.20 * firmness_score
            + 0.20 * stickiness_score
            + 0.10 * temp_score
        )

        return PastaCookingResult(
            core_temp_c=round(float(core_temp), 2),
            water_uptake_pct=round(float(water_uptake), 2),
            cooking_loss_pct=round(float(cooking_loss), 2),
            firmness_index=round(firmness, 4),
            stickiness_index=round(stickiness, 4),
            quality_score=round(quality, 4),
        )
