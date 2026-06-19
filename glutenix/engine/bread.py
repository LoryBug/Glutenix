from dataclasses import dataclass

import numpy as np

from glutenix.engine.baking import BakingParams, BakingSimulator
from glutenix.engine.blend import BlendProperties
from glutenix.engine.fermentation import FermentationParams, FermentationSimulator


@dataclass
class BreadQualityParams:
    hydration_pct: float = 100.0
    fermentation_temp_c: float = 30.0
    fermentation_time_min: float = 60.0
    baking_temp_c: float = 190.0
    baking_time_min: float = 40.0
    dough_thickness_cm: float = 5.0
    yeast_pct: float = 3.0
    sugar_pct: float = 3.0
    fat_pct: float = 0.0
    chemical_leavening_pct: float = 0.0
    emulsifier_pct: float = 0.0
    storage_days: float = 1.0


@dataclass
class BreadQualityResult:
    specific_volume_cm3_g: float
    crumb_hardness_n: float
    moisture_retention_index: float
    staling_risk: float
    structure_index: float
    process_family: str
    calibration_confidence: str
    calibration_score: float
    calibration_notes: list[str]
    core_temp_c: float
    crust_temp_c: float


class BreadQualitySimulator:
    def __init__(self, params: BreadQualityParams | None = None):
        self.params = params or BreadQualityParams()

    @staticmethod
    def _ingredient_fraction(blend_props: BlendProperties, token: str) -> float:
        token = token.lower()
        return sum(
            item["proportion"]
            for item in blend_props.ingredients_detail
            if token in item["name"].lower()
        )

    def simulate(self, blend_props: BlendProperties) -> BreadQualityResult:
        p = self.params
        if p.hydration_pct <= 0:
            raise ValueError("hydration_pct must be positive")
        if p.fermentation_time_min < 0:
            raise ValueError("fermentation_time_min must be non-negative")
        if p.baking_time_min <= 0:
            raise ValueError("baking_time_min must be positive")
        if p.dough_thickness_cm <= 0:
            raise ValueError("dough_thickness_cm must be positive")
        if p.yeast_pct < 0 or p.sugar_pct < 0 or p.fat_pct < 0:
            raise ValueError("yeast_pct, sugar_pct, and fat_pct must be non-negative")

        fermentation = FermentationSimulator(
            FermentationParams(
                temp_c=p.fermentation_temp_c,
                yeast_conc=max(p.yeast_pct / 3.0, 0.05),
                initial_sugar=max(p.sugar_pct, 0.1),
            )
        ).simulate(
            viscosity_index=blend_props.viscosity_index,
            duration_min=max(p.fermentation_time_min, 1.0),
        )
        baking = BakingSimulator(
            BakingParams(
                oven_temp_c=p.baking_temp_c,
                baking_time_min=p.baking_time_min,
                dough_thickness_cm=p.dough_thickness_cm,
            )
        ).simulate(
            gelatinization_temp_min=blend_props.gelatinization_temp_min,
            gelatinization_temp_max=blend_props.gelatinization_temp_max,
        )

        chickpea = self._ingredient_fraction(blend_props, "chickpea")
        millet = self._ingredient_fraction(blend_props, "millet")
        commercial_mix = self._ingredient_fraction(blend_props, "commercial gluten-free bread mix")
        whey = self._ingredient_fraction(blend_props, "whey")

        structure = float(np.clip(
            0.32 * blend_props.viscosity_index / 2.4
            + 0.24 * blend_props.hydrocolloid_pct / 0.045
            + 0.22 * blend_props.protein_pct / 12.0
            + 0.22 * blend_props.amylose_pct / 25.0,
            0.0,
            1.6,
        ))
        hydration_fit = float(np.exp(-0.5 * ((p.hydration_pct - 105.0) / 28.0) ** 2))
        bake_fit = float(np.exp(-0.5 * ((baking.core_temp_c - 96.0) / 9.0) ** 2))
        fermentation_volume = fermentation.final_volume_increase
        leavening_boost = 0.28 * float(np.tanh(p.chemical_leavening_pct / 1.0))
        emulsifier_effect = -0.16 * float(np.tanh(p.emulsifier_pct / 0.3))

        specific_volume = (
            1.20
            + 1.15 * fermentation_volume
            + 0.50 * structure
            + 0.35 * hydration_fit
            + 0.25 * bake_fit
            + 0.55 * commercial_mix
            + leavening_boost
            + emulsifier_effect
            - 0.28 * chickpea
            - 0.18 * millet
            + 0.10 * whey
        )
        specific_volume = float(np.clip(specific_volume, 0.8, 5.0))

        storage_factor = 1.0 + 0.08 * max(p.storage_days - 1.0, 0.0)
        staling_drive = float(np.clip(
            0.34
            + 0.28 * chickpea
            + 0.18 * millet
            + 0.16 * blend_props.starch_pct / 80.0
            - 0.18 * blend_props.hydrocolloid_pct / 0.05
            - 0.10 * min(p.fat_pct / 8.0, 1.0),
            0.05,
            1.2,
        ))
        hardness = (
            18.0 / max(specific_volume, 0.8) ** 1.35
            + 14.0 * staling_drive * storage_factor
            + 8.0 * chickpea
            + 2.0 * millet
            - 2.0 * whey
        )
        hardness = float(np.clip(hardness, 1.0, 80.0))
        moisture_retention = float(np.clip(
            0.45
            + 0.20 * hydration_fit
            + 0.22 * blend_props.hydrocolloid_pct / 0.05
            + 0.08 * min(p.fat_pct / 8.0, 1.0)
            - 0.12 * max(p.storage_days - 1.0, 0.0) / 7.0,
            0.0,
            1.0,
        ))

        notes: list[str] = []
        if commercial_mix > 0.5:
            process_family = "commercial_mix_bread"
            calibration_score = 0.55
            notes.append("Commercial gluten-free bread mix is represented as an approximate aggregate ingredient.")
        elif millet > 0.35:
            process_family = "millet_cultivar_bread"
            calibration_score = 0.6
            notes.append("Covered by proso millet gluten-free bread literature, but cultivar-specific starch data is simplified.")
        elif chickpea > 0.25 or whey > 0.05:
            process_family = "protein_enriched_bread"
            calibration_score = 0.6
            notes.append("Covered by rice/chickpea or rice/whey protein gluten-free bread literature.")
        else:
            process_family = "generic_gluten_free_bread"
            calibration_score = 0.35
            notes.append("Generic gluten-free bread mode has limited direct calibration coverage.")

        if calibration_score >= 0.75:
            confidence = "high"
        elif calibration_score >= 0.5:
            confidence = "medium"
        else:
            confidence = "low"

        return BreadQualityResult(
            specific_volume_cm3_g=round(specific_volume, 4),
            crumb_hardness_n=round(hardness, 4),
            moisture_retention_index=round(moisture_retention, 4),
            staling_risk=round(staling_drive, 4),
            structure_index=round(structure, 4),
            process_family=process_family,
            calibration_confidence=confidence,
            calibration_score=round(calibration_score, 4),
            calibration_notes=notes,
            core_temp_c=round(float(baking.core_temp_c), 2),
            crust_temp_c=round(float(baking.crust_temp_c), 2),
        )
