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
    tg_pct: float = 0.0
    storage_days: float = 1.0


@dataclass
class BreadQualityResult:
    specific_volume_cm3_g: float
    crumb_hardness_n: float
    porosity_pct: float
    moisture_retention_index: float
    staling_risk: float
    structure_index: float
    process_family: str
    calibration_confidence: str
    calibration_score: float
    calibration_notes: list[str]
    core_temp_c: float
    crust_temp_c: float


STARCH_VOLUME_MODIFIERS: dict[str, float] = {
    "rice": -0.25,
    "maize": +0.10,
    "tapioca": +0.05,
    "potato": +0.05,
    "millet": -0.02,
    "buckwheat": -0.05,
}


# Sparse diagnostic factors grounded in Loncaric 2026, Wojcik 2021,
# Kahraman 2022, and Bianchi 2026 protein-enriched bread records.
PROTEIN_SOURCE_EFFECTS: dict[str, dict[str, float]] = {
    "legume_flour": {"volume": -0.32, "hardness": 8.0, "porosity": -2.0, "staling": 0.28},
    "dairy_concentrate": {"volume": 0.06, "hardness": -3.0, "porosity": -1.5, "staling": -0.04},
    "protein_isolate": {"volume": -0.65, "hardness": 11.0, "porosity": -3.0, "staling": 0.15},
    "seed_flour": {"volume": -0.06, "hardness": 1.5, "porosity": -0.8, "staling": 0.05},
}

PROTEIN_PROCESS_EFFECTS: dict[str, dict[str, float]] = {
    "raw": {"volume": 0.0, "hardness": 0.0, "porosity": 0.0, "staling": 0.0},
    "roasted": {"volume": 1.4, "hardness": -28.0, "porosity": 32.0, "staling": -0.35},
    "dehulled": {"volume": 0.85, "hardness": 2.0, "porosity": 1.0, "staling": 0.03},
    "fermented": {"volume": 0.5, "hardness": -4.0, "porosity": 5.0, "staling": -0.10},
    "hydrolyzed": {"volume": 0.2, "hardness": -2.0, "porosity": 2.0, "staling": -0.05},
    "isolated": {"volume": 0.0, "hardness": 0.0, "porosity": 0.0, "staling": 0.0},
}


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

    @staticmethod
    def _protein_source_category(name: str) -> str | None:
        lowered = name.lower()
        if "whey" in lowered or "caseinate" in lowered:
            return "dairy_concentrate"
        if "soy protein" in lowered or "pea protein" in lowered or "isolate" in lowered:
            return "protein_isolate"
        if any(token in lowered for token in ("chickpea", "lentil", "faba", "pea flour")):
            return "legume_flour"
        if "flaxseed" in lowered or "seed flour" in lowered:
            return "seed_flour"
        return None

    @staticmethod
    def _protein_processing_state(name: str) -> str:
        lowered = name.lower()
        if "roasted" in lowered:
            return "roasted"
        if "dehulled" in lowered:
            return "dehulled"
        if "fermented" in lowered:
            return "fermented"
        if "hydrolyzed" in lowered or "hydrolysed" in lowered:
            return "hydrolyzed"
        if "isolate" in lowered or "isolated" in lowered or "protein powder" in lowered:
            return "isolated"
        return "raw"

    def _protein_structure_effects(self, blend_props: BlendProperties) -> tuple[dict[str, float], dict[str, float]]:
        effects = {"volume": 0.0, "hardness": 0.0, "porosity": 0.0, "staling": 0.0}
        category_fractions = {category: 0.0 for category in PROTEIN_SOURCE_EFFECTS}
        for item in blend_props.ingredients_detail:
            category = self._protein_source_category(str(item.get("name", "")))
            if category is None:
                continue
            fraction = float(item.get("proportion", 0.0))
            category_fractions[category] += fraction
            state = self._protein_processing_state(str(item.get("name", "")))
            state_effects = PROTEIN_PROCESS_EFFECTS.get(state, PROTEIN_PROCESS_EFFECTS["raw"])
            for metric in effects:
                effects[metric] += fraction * (
                    PROTEIN_SOURCE_EFFECTS[category][metric]
                    + state_effects[metric]
                )
        return effects, category_fractions

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
        if p.yeast_pct < 0 or p.sugar_pct < 0 or p.fat_pct < 0 or p.tg_pct < 0:
            raise ValueError("yeast_pct, sugar_pct, fat_pct, and tg_pct must be non-negative")

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

        millet = self._ingredient_fraction(blend_props, "millet")
        commercial_mix = self._ingredient_fraction(blend_props, "commercial gluten-free bread mix")
        hpmc = self._ingredient_fraction(blend_props, "hpmc")
        guar = self._ingredient_fraction(blend_props, "guar")
        xanthan = self._ingredient_fraction(blend_props, "xanthan")
        protein_effects, protein_categories = self._protein_structure_effects(blend_props)
        protein_enrichment_fraction = (
            protein_categories["legume_flour"]
            + protein_categories["dairy_concentrate"]
            + protein_categories["protein_isolate"]
        )

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

        starch_mod = STARCH_VOLUME_MODIFIERS.get(blend_props.dominant_starch_type or "", 0.0)
        if blend_props.starch_fraction > 0:
            starch_mod *= min(blend_props.starch_fraction, 1.0)

        specific_volume = (
            1.20
            + 1.15 * fermentation_volume
            + 0.50 * structure
            + 0.35 * hydration_fit
            + 0.25 * bake_fit
            + 0.55 * commercial_mix
            + leavening_boost
            + emulsifier_effect
            + starch_mod
            - 0.18 * millet
            + protein_effects["volume"]
        )
        specific_volume = float(np.clip(specific_volume, 0.8, 5.0))

        storage_factor = 1.0 + 0.08 * max(p.storage_days - 1.0, 0.0)
        staling_drive = float(np.clip(
            0.34
            + protein_effects["staling"]
            + 0.18 * millet
            + 0.16 * blend_props.starch_pct / 80.0
            - 0.18 * blend_props.hydrocolloid_pct / 0.05
            - 0.10 * min(p.fat_pct / 8.0, 1.0),
            0.05,
            1.2,
        ))

        hpmc_frac = self._ingredient_fraction(blend_props, "hpmc")
        psyllium_frac = self._ingredient_fraction(blend_props, "psyllium")
        xanthan_frac = self._ingredient_fraction(blend_props, "xanthan")

        is_hc_controlled_hardness = (
            blend_props.hydrocolloid_pct > 0.001
            and protein_enrichment_fraction <= 0.05
        )
        if is_hc_controlled_hardness:
            hc_hardness_mod = (
                6.0 * (psyllium_frac / blend_props.hydrocolloid_pct)
                + 3.0 * (xanthan_frac / blend_props.hydrocolloid_pct)
            ) * min(blend_props.hydrocolloid_pct / 0.03, 1.0)
        else:
            hc_hardness_mod = 0.0

        hardness = (
            18.0 / max(specific_volume, 0.8) ** 1.35
            + 14.0 * staling_drive * storage_factor
            + 2.0 * millet
            + protein_effects["hardness"]
            + hc_hardness_mod
        )
        hardness = float(np.clip(hardness, 1.0, 80.0))
        porosity = float(np.clip(
            18.0
            + 4.8 * specific_volume
            + 5.0 * structure
            + 3.2 * hydration_fit
            + 2.5 * min(blend_props.hydrocolloid_pct / 0.025, 1.2)
            + protein_effects["porosity"]
            - 1.0 * millet,
            8.0,
            55.0,
        ))
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
        if p.tg_pct > 0 and hpmc + guar + xanthan > 0:
            process_family = "enzyme_hydrocolloid_bread"
            calibration_score = 0.3
            notes.append("Microbial transglutaminase is present, but enzyme-driven bread structure is not modeled yet.")
        elif p.tg_pct > 0:
            process_family = "enzyme_bread"
            calibration_score = 0.25
            notes.append("Microbial transglutaminase is present, but enzyme-driven bread structure is not modeled yet.")
        elif commercial_mix > 0.5:
            process_family = "commercial_mix_bread"
            calibration_score = 0.55
            notes.append("Commercial gluten-free bread mix is represented as an approximate aggregate ingredient.")
        elif millet > 0.35:
            process_family = "millet_cultivar_bread"
            calibration_score = 0.6
            notes.append("Covered by proso millet gluten-free bread literature, but cultivar-specific starch data is simplified.")
        elif protein_enrichment_fraction > 0.045:
            process_family = "protein_enriched_bread"
            calibration_score = 0.6
            notes.append("Covered by legume, dairy, or isolate protein-enriched gluten-free bread literature.")
        elif blend_props.hydrocolloid_pct >= 0.015 and hpmc + guar + xanthan > 0:
            process_family = "hydrocolloid_bread"
            calibration_score = 0.55
            notes.append("Covered by hydrocolloid-combination gluten-free bread literature; volume and texture coverage remains limited.")
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
            porosity_pct=round(porosity, 4),
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
