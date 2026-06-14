from dataclasses import dataclass, field

import numpy as np

from glutenix.db.models import Ingredient


@dataclass
class BlendProperties:
    protein_pct: float = 0.0
    starch_pct: float = 0.0
    fat_pct: float = 0.0
    fiber_pct: float = 0.0
    moisture_pct: float = 0.0
    ash_pct: float = 0.0

    water_absorption: float = 1.0
    gelatinization_temp_min: float = 65.0
    gelatinization_temp_max: float = 75.0
    amylose_pct: float = 20.0

    kcal_per_100g: float = 0.0
    sugars_pct: float = 0.0
    saturated_fat_pct: float = 0.0
    sodium_mg_per_100g: float = 0.0

    viscosity_index: float = 1.0

    hydrocolloid_pct: float = 0.0

    ingredients_detail: list[dict] = field(default_factory=list)


class BlendCalculator:
    ADDITIVE_PROPS = [
        "protein_pct",
        "starch_pct",
        "fat_pct",
        "fiber_pct",
        "moisture_pct",
        "ash_pct",
        "kcal_per_100g",
        "sugars_pct",
        "saturated_fat_pct",
        "sodium_mg_per_100g",
    ]

    def calculate(
        self,
        ingredient_data: list[tuple[Ingredient, float]],
    ) -> BlendProperties:
        total_weight = sum(prop for _, prop in ingredient_data)
        if abs(total_weight - 1.0) > 1e-6:
            raise ValueError(
                f"Proportions must sum to 1.0, got {total_weight}"
            )

        props = BlendProperties()

        self._compute_additive_props(props, ingredient_data)
        self._compute_water_absorption(props, ingredient_data)
        self._compute_gelatinization(props, ingredient_data)
        self._compute_amylose(props, ingredient_data)
        self._compute_viscosity_index(props, ingredient_data)
        self._compute_hydrocolloid_pct(props, ingredient_data)

        props.ingredients_detail = [
            {"name": ing.name, "proportion": prop, "category": ing.category}
            for ing, prop in ingredient_data
        ]

        return props

    def _compute_additive_props(
        self,
        props: BlendProperties,
        ingredient_data: list[tuple[Ingredient, float]],
    ) -> None:
        for prop in self.ADDITIVE_PROPS:
            values = []
            for ing, pct in ingredient_data:
                val = getattr(ing, prop)
                if val is not None:
                    values.append(val * pct)
            if values:
                setattr(props, prop, sum(values))

    def _compute_water_absorption(
        self,
        props: BlendProperties,
        ingredient_data: list[tuple[Ingredient, float]],
    ) -> None:
        values = []
        for ing, pct in ingredient_data:
            if ing.water_absorption is not None:
                values.append(ing.water_absorption * pct)
        if values:
            props.water_absorption = sum(values)

    def _compute_gelatinization(
        self,
        props: BlendProperties,
        ingredient_data: list[tuple[Ingredient, float]],
    ) -> None:
        num_min, num_max, denom = 0.0, 0.0, 0.0
        for ing, pct in ingredient_data:
            if (
                ing.gelatinization_temp_min is not None
                and ing.gelatinization_temp_max is not None
            ):
                w = (ing.starch_pct or 0) * pct
                num_min += ing.gelatinization_temp_min * w
                num_max += ing.gelatinization_temp_max * w
                denom += w

        if denom > 0:
            props.gelatinization_temp_min = num_min / denom
            props.gelatinization_temp_max = num_max / denom

    def _compute_amylose(
        self,
        props: BlendProperties,
        ingredient_data: list[tuple[Ingredient, float]],
    ) -> None:
        values = []
        for ing, pct in ingredient_data:
            if ing.amylose_pct is not None and ing.starch_pct is not None:
                values.append(ing.amylose_pct * ing.starch_pct / 100 * pct)
        if values:
            if props.starch_pct > 0:
                props.amylose_pct = (
                    sum(values) / props.starch_pct * 100
                )

    def _compute_viscosity_index(
        self,
        props: BlendProperties,
        ingredient_data: list[tuple[Ingredient, float]],
    ) -> None:
        idx = 0.0
        for ing, pct in ingredient_data:
            base = 1.0
            if ing.category == "starch":
                if "tapioca" in ing.name.lower():
                    base = 2.5
                elif "potato" in ing.name.lower():
                    base = 3.0
                elif "corn" in ing.name.lower():
                    base = 1.5
            elif ing.category == "hydrocolloid":
                if "xanthan" in ing.name.lower():
                    base = 10.0
                elif "psyllium" in ing.name.lower():
                    base = 8.0
                elif "guar" in ing.name.lower():
                    base = 7.0
                elif "hpmc" in ing.name.lower():
                    base = 6.0
            elif ing.category == "flour":
                if "oat" in ing.name.lower():
                    base = 1.4
                elif "buckwheat" in ing.name.lower():
                    base = 1.3
                elif "almond" in ing.name.lower():
                    base = 0.5

            idx += base * pct

        props.viscosity_index = idx

    def _compute_hydrocolloid_pct(
        self,
        props: BlendProperties,
        ingredient_data: list[tuple[Ingredient, float]],
    ) -> None:
        props.hydrocolloid_pct = sum(
            pct for ing, pct in ingredient_data if ing.category == "hydrocolloid"
        )
