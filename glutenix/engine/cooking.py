from dataclasses import dataclass

import numpy as np

from glutenix.engine.blend import BlendProperties


@dataclass
class PastaCookingParams:
    water_temp_c: float = 98.0
    cooking_time_min: float = 6.0
    pasta_thickness_mm: float = 2.0
    initial_temp_c: float = 20.0
    water_to_flour_ratio: float | None = None
    calcium_lactate_m: float = 0.0
    calcium_bath_time_min: float = 0.0
    dough_heat_temp_c: float = 0.0
    dough_heat_time_min: float = 0.0
    dried_pasta: bool = False
    extrusion_moisture_pct: float | None = None
    extrusion_barrel_temp_c: float | None = None
    screw_speed_rpm: float | None = None
    instant_pasta: bool = False


@dataclass
class PastaCookingResult:
    core_temp_c: float
    water_uptake_pct: float
    cooking_loss_pct: float
    swelling_index: float
    firmness_index: float
    stickiness_index: float
    quality_score: float
    gelation_index: float
    pregelatinization_index: float
    syneresis_index: float
    starch_leaching_index: float
    process_family: str
    calibration_confidence: str
    calibration_score: float
    calibration_notes: list[str]


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
        if p.water_to_flour_ratio is not None and p.water_to_flour_ratio <= 0:
            raise ValueError("water_to_flour_ratio must be positive")
        if p.calcium_lactate_m < 0:
            raise ValueError("calcium_lactate_m must be non-negative")
        if p.calcium_bath_time_min < 0:
            raise ValueError("calcium_bath_time_min must be non-negative")
        if p.dough_heat_time_min < 0:
            raise ValueError("dough_heat_time_min must be non-negative")
        if p.extrusion_moisture_pct is not None and p.extrusion_moisture_pct <= 0:
            raise ValueError("extrusion_moisture_pct must be positive")
        if p.extrusion_barrel_temp_c is not None and p.extrusion_barrel_temp_c <= 0:
            raise ValueError("extrusion_barrel_temp_c must be positive")
        if p.screw_speed_rpm is not None and p.screw_speed_rpm <= 0:
            raise ValueError("screw_speed_rpm must be positive")

        temp_factor = float(np.clip((p.water_temp_c - 60.0) / 38.0, 0.05, 1.25))
        thickness_factor = max(p.pasta_thickness_mm / 2.0, 0.25)

        core_temp = p.initial_temp_c + (p.water_temp_c - p.initial_temp_c) * (
            1.0 - np.exp(-0.55 * p.cooking_time_min / (thickness_factor**2))
        )

        hydrocolloid = blend_props.hydrocolloid_pct
        alginate = self._ingredient_fraction(blend_props, "alginate")
        kgm = max(
            self._ingredient_fraction(blend_props, "konjac"),
            self._ingredient_fraction(blend_props, "glucomannan"),
        )
        curdlan = self._ingredient_fraction(blend_props, "curdlan")
        soy_protein = self._ingredient_fraction(blend_props, "soy protein")
        waxy_rice = self._ingredient_fraction(blend_props, "sweet rice") + self._ingredient_fraction(blend_props, "waxy")
        high_amylose_rice = self._ingredient_fraction(blend_props, "high-amylose rice")
        white_rice = self._ingredient_fraction(blend_props, "white rice")
        buckwheat = self._ingredient_fraction(blend_props, "buckwheat")
        protein = blend_props.protein_pct
        amylose = blend_props.amylose_pct
        water_absorption = blend_props.water_absorption
        water_to_flour = p.water_to_flour_ratio

        structure = float(np.clip(
            0.28 * protein / 12.0
            + 0.28 * amylose / 28.0
            + 0.24 * hydrocolloid / 0.025
            + 0.20 * alginate / 0.015,
            0.0,
            1.8,
        ))
        alginate_level = float(np.clip(alginate / 0.015, 0.0, 1.5))
        if p.calcium_lactate_m > 0 and p.calcium_bath_time_min > 0:
            calcium_factor = 1.0 - np.exp(-p.calcium_lactate_m / 0.035)
            bath_factor = 1.0 - np.exp(-p.calcium_bath_time_min / 10.0)
            water_factor = 1.0
            if water_to_flour is not None:
                water_factor = float(np.clip(0.65 + 0.07 * water_to_flour, 0.65, 1.25))
            alginate_gel = float(np.clip(alginate_level * calcium_factor * bath_factor * water_factor, 0.0, 1.6))
        else:
            alginate_gel = float(np.clip(0.55 * alginate_level, 0.0, 0.8))

        if p.dough_heat_temp_c > 0 and p.dough_heat_time_min > 0:
            gel_mid = (blend_props.gelatinization_temp_min + blend_props.gelatinization_temp_max) / 2.0
            heat_factor = float(np.clip((p.dough_heat_temp_c - gel_mid + 8.0) / 18.0, 0.0, 1.15))
            time_heat_factor = float(1.0 - np.exp(-p.dough_heat_time_min / 25.0))
            water_factor = 1.0
            if water_to_flour is not None:
                low_water = max(0.0, (3.0 - water_to_flour) / 2.0)
                excess_water = max(0.0, (water_to_flour - 8.0) / 5.0)
                water_factor = float(np.clip(1.0 - 0.35 * low_water - 0.12 * excess_water, 0.45, 1.05))
            pregelatinization = float(np.clip(heat_factor * time_heat_factor * water_factor, 0.0, 1.0))
        else:
            pregelatinization = 0.0

        low_water_damage = 0.0
        excess_water = 0.0
        gel_syneresis_drive = 0.0
        dilution_syneresis_drive = 0.0
        high_alginate_syneresis = 0.0
        if water_to_flour is not None:
            low_water_damage = float(np.clip((3.0 - water_to_flour) / 2.0, 0.0, 1.0))
            excess_water = float(np.clip((water_to_flour - 5.0) / 5.0, 0.0, 1.4))
            high_alginate_syneresis = float(np.clip((alginate_level - 0.65) / 0.35, 0.0, 1.0))
            gel_syneresis_drive = high_alginate_syneresis * float(np.clip((water_to_flour - 2.0) / 4.0, 0.0, 0.85))
            dilution_syneresis_drive = float(np.clip((water_to_flour - 8.0) / 2.0, 0.0, 1.0)) * (
                0.7 + 0.5 * min(alginate_level, 1.0)
            )

        syneresis_drive = max(gel_syneresis_drive, dilution_syneresis_drive)
        cooking_time_release = 1.0 - np.exp(-p.cooking_time_min / 7.0)
        syneresis = float(np.clip(
            alginate_gel
            * syneresis_drive
            * cooking_time_release,
            0.0,
            1.4,
        ))

        if water_to_flour is None:
            max_uptake = float(np.clip(45.0 + 35.0 * water_absorption, 55.0, 130.0))
            hydration_rate = 0.32 * temp_factor / thickness_factor
            water_uptake = max_uptake * (1.0 - np.exp(-hydration_rate * p.cooking_time_min))
        else:
            max_uptake = float(np.clip(
                18.0
                + 7.0 * (1.0 - min(alginate_gel, 1.0))
                + 5.0 * low_water_damage
                + 2.0 * water_absorption,
                8.0,
                34.0,
            ))
            hydration_rate = 0.075 * temp_factor / thickness_factor
            gel_water_release = 8.0 * gel_syneresis_drive * cooking_time_release * (1.0 - min(dilution_syneresis_drive, 1.0))
            dilution_water_release = (
                14.0
                * min(dilution_syneresis_drive, 1.0)
                * cooking_time_release
                * (1.0 - 0.7 * high_alginate_syneresis)
            )
            water_uptake = (
                max_uptake * (1.0 - np.exp(-hydration_rate * p.cooking_time_min))
                - 24.0 * syneresis
                - gel_water_release
                - dilution_water_release
            )

        if p.dried_pasta:
            kgm_level = float(np.clip(kgm / 0.045, 0.0, 1.4))
            curdlan_level = float(np.clip(curdlan / 0.022, 0.0, 1.4))
            soy_pct = soy_protein * 100.0
            soy_uptake = 8.0 * float(np.clip(soy_pct / 10.0, 0.0, 1.0))
            extrusion_factor = 1.0
            if p.extrusion_moisture_pct is not None:
                extrusion_factor = float(np.clip(p.extrusion_moisture_pct / 32.0, 0.75, 1.25))
            water_uptake = float(np.clip(
                42.0
                + 15.0 * kgm_level
                - 16.0 * np.sqrt(curdlan_level)
                + 7.0 * curdlan_level
                + soy_uptake
                + 4.0 * (extrusion_factor - 1.0),
                20.0,
                260.0,
            ))
            if p.instant_pasta:
                extrusion_moisture = p.extrusion_moisture_pct or 30.0
                barrel_temp = p.extrusion_barrel_temp_c or 100.0
                screw_speed = p.screw_speed_rpm or 80.0
                water_uptake = float(np.clip(
                    210.0
                    + 35.0 * buckwheat
                    + 0.8 * (extrusion_moisture - 30.0)
                    + 0.35 * (barrel_temp - 100.0)
                    - 0.08 * (screw_speed - 80.0),
                    140.0,
                    260.0,
                ))

        process_family = "dried_extruded" if p.dried_pasta else "generic_fresh"
        calibration_score = 0.25
        notes: list[str] = []
        if p.dried_pasta:
            if p.instant_pasta:
                process_family = "instant_extruded"
            rice_like = high_amylose_rice + waxy_rice >= 0.75
            instant_rice_like = p.instant_pasta and white_rice + buckwheat >= 0.75
            studied_additive = kgm > 0.0 or curdlan > 0.0 or soy_protein > 0.0 or waxy_rice > 0.0
            if instant_rice_like and p.extrusion_moisture_pct is not None:
                calibration_score = 0.65
                notes.append("Covered by instant extrusion-cooked rice or rice-buckwheat pasta literature.")
            elif rice_like and studied_additive and p.extrusion_moisture_pct is not None:
                calibration_score = 0.75
                notes.append("Covered by dried-extruded rice pasta literature with KGM/curdlan or SPI.")
            elif rice_like:
                calibration_score = 0.5
                notes.append("Rice-based dried pasta is partially covered, but additives/process differ from current literature.")
            else:
                notes.append("Dried pasta composition is outside the current rice-pasta calibration set.")
        elif alginate > 0.0 and p.calcium_lactate_m > 0 and p.calcium_bath_time_min > 0:
            process_family = "fresh_calcium_gel"
            ratio_covered = water_to_flour is not None and 2.0 <= water_to_flour <= 10.0
            alginate_covered = 0.008 <= alginate <= 0.018
            if ratio_covered and alginate_covered:
                calibration_score = 0.85
                notes.append("Covered by calcium-alginate fresh pasta literature.")
            else:
                calibration_score = 0.55
                notes.append("Calcium-alginate mechanism is covered, but ratio or alginate level is extrapolated.")
        else:
            notes.append("Generic fresh pasta mode has no direct literature calibration yet.")

        if calibration_score >= 0.8:
            calibration_confidence = "high"
        elif calibration_score >= 0.5:
            calibration_confidence = "medium"
        else:
            calibration_confidence = "low"

        optimal_time = 5.5 * thickness_factor / temp_factor
        undercook = max(0.0, (optimal_time - p.cooking_time_min) / optimal_time)
        overcook = max(0.0, (p.cooking_time_min - optimal_time) / optimal_time)

        starch_leaching = float(np.clip(
            0.32 * (1.0 - min(structure / 1.4, 1.0))
            + 0.30 * (1.0 - min(alginate_gel, 1.0))
            + 0.20 * (1.0 - pregelatinization)
            + 0.12 * low_water_damage
            + 0.10 * max(0.0, overcook)
            - 0.10 * syneresis,
            0.0,
            1.4,
        ))

        overcook_loss = 2.1 * overcook * (1.0 - 0.75 * min(alginate_gel, 1.0))
        loss = (
            6.2
            - 2.0 * structure
            - 5.0 * alginate_gel
            - 1.15 * pregelatinization
            + overcook_loss
            + 1.2 * max(0.0, water_uptake - 85.0) / 45.0
            + 0.8 * blend_props.starch_pct / 85.0
            + 0.45 * low_water_damage
            + 0.35 * excess_water * (1.0 - min(alginate_gel, 1.0))
            + 1.2 * starch_leaching
            - 0.10 * syneresis
        )
        if p.dried_pasta:
            kgm_level = float(np.clip(kgm / 0.045, 0.0, 1.4))
            curdlan_level = float(np.clip(curdlan / 0.022, 0.0, 1.4))
            soy_level = float(np.clip(soy_protein / 0.05, 0.0, 2.5))
            soy_network = 9.0 * np.exp(-0.5 * ((soy_level - 1.0) / 0.55) ** 2)
            high_soy_penalty = 0.5 * max(0.0, soy_level - 1.0)
            loss = (
                22.7
                + 27.0 * waxy_rice
                + 1.7 * kgm_level
                - 5.4 * np.sqrt(curdlan_level)
                - soy_network
                + high_soy_penalty
                + 0.35 * max(0.0, overcook)
                + 0.6 * (1.0 - min(amylose / 28.0, 1.0))
            )
            if p.instant_pasta:
                extrusion_moisture = p.extrusion_moisture_pct or 30.0
                barrel_temp = p.extrusion_barrel_temp_c or 100.0
                screw_speed = p.screw_speed_rpm or 80.0
                loss = (
                    4.7
                    + 0.9 * buckwheat
                    + 0.25 * (extrusion_moisture - 30.0)
                    - 0.007 * (barrel_temp - 100.0)
                    + 0.005 * (screw_speed - 80.0)
                )
        cooking_loss = float(np.clip(loss, 0.35, 30.0))

        if water_to_flour is None:
            swelling_index = float(np.clip(2.2 + water_uptake / 22.0, 2.0, 10.0))
        else:
            swelling_index = float(np.clip(
                2.0
                + 0.72 * water_to_flour
                + 0.8 * pregelatinization
                - 0.55 * syneresis
                - 0.35 * low_water_damage,
                2.0,
                10.5,
            ))

        firmness = float(np.clip(
            0.72
            + 0.18 * structure
            + 0.18 * alginate_gel
            + 0.10 * pregelatinization
            + 0.08 * syneresis
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
            - 0.18 * alginate_gel
            - 0.06 * pregelatinization,
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
            swelling_index=round(swelling_index, 4),
            firmness_index=round(firmness, 4),
            stickiness_index=round(stickiness, 4),
            quality_score=round(quality, 4),
            gelation_index=round(alginate_gel, 4),
            pregelatinization_index=round(pregelatinization, 4),
            syneresis_index=round(syneresis, 4),
            starch_leaching_index=round(starch_leaching, 4),
            process_family=process_family,
            calibration_confidence=calibration_confidence,
            calibration_score=round(calibration_score, 4),
            calibration_notes=notes,
        )


def pasta_v1_process_params(
    blend_props: BlendProperties,
    *,
    water_temp_c: float,
    cooking_time_min: float,
) -> PastaCookingParams:
    alginate = PastaCookingSimulator._ingredient_fraction(blend_props, "alginate")
    if alginate > 0:
        return PastaCookingParams(
            water_temp_c=100.0,
            cooking_time_min=cooking_time_min,
            pasta_thickness_mm=2.0,
            water_to_flour_ratio=3.0,
            calcium_lactate_m=0.1,
            calcium_bath_time_min=30.0,
        )
    return PastaCookingParams(
        water_temp_c=water_temp_c,
        cooking_time_min=cooking_time_min,
        pasta_thickness_mm=2.0,
        water_to_flour_ratio=0.9,
    )


def serialize_pasta_process_params(params: PastaCookingParams) -> dict[str, float]:
    payload = {
        "water_temp_c": params.water_temp_c,
        "cooking_time_min": params.cooking_time_min,
        "pasta_thickness_mm": params.pasta_thickness_mm,
        "water_to_flour_ratio": params.water_to_flour_ratio,
    }
    if params.calcium_lactate_m > 0:
        payload["calcium_lactate_m"] = params.calcium_lactate_m
    if params.calcium_bath_time_min > 0:
        payload["calcium_bath_time_min"] = params.calcium_bath_time_min
    return {key: value for key, value in payload.items() if value is not None}
