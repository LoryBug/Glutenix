import numpy as np

from glutenix.db.models import Ingredient
from glutenix.engine.baking import BakingParams, BakingSimulator
from glutenix.engine.blend import BlendCalculator, BlendProperties
from glutenix.engine.bread import BreadQualityParams, BreadQualitySimulator
from glutenix.engine.cooking import (
    PastaCookingParams,
    PastaCookingResult,
    PastaCookingSimulator,
)
from glutenix.engine.fermentation import (
    FermentationParams,
    FermentationResult,
    FermentationSimulator,
)


class TestBlendCalculator:
    def test_additive_properties(self):
        i1 = Ingredient(
            name="Rice",
            category="flour",
            protein_pct=6.0,
            starch_pct=80.0,
            fat_pct=1.0,
            fiber_pct=2.0,
            moisture_pct=12.0,
            ash_pct=0.5,
        )
        i2 = Ingredient(
            name="Tapioca",
            category="starch",
            protein_pct=0.2,
            starch_pct=88.0,
            fat_pct=0.1,
            fiber_pct=0.5,
            moisture_pct=11.0,
            ash_pct=0.1,
        )

        calc = BlendCalculator()
        props = calc.calculate([(i1, 0.7), (i2, 0.3)])

        assert abs(props.protein_pct - (6.0 * 0.7 + 0.2 * 0.3)) < 1e-6
        assert abs(props.starch_pct - (80.0 * 0.7 + 88.0 * 0.3)) < 1e-6
        assert abs(props.fat_pct - (1.0 * 0.7 + 0.1 * 0.3)) < 1e-6

    def test_single_ingredient(self):
        ing = Ingredient(
            name="Buckwheat",
            category="flour",
            protein_pct=11.1,
            starch_pct=67.0,
            fat_pct=3.0,
            water_absorption=1.6,
        )
        calc = BlendCalculator()
        props = calc.calculate([(ing, 1.0)])
        assert abs(props.protein_pct - 11.1) < 1e-6
        assert abs(props.water_absorption - 1.6) < 1e-6

    def test_sum_must_be_one(self):
        calc = BlendCalculator()
        import pytest

        with pytest.raises(ValueError):
            calc.calculate([])

    def test_viscosity_index(self):
        starch = Ingredient(name="Potato starch", category="starch")
        flour = Ingredient(name="Rice flour", category="flour")
        gum = Ingredient(name="Xanthan gum", category="hydrocolloid")

        calc = BlendCalculator()
        props = calc.calculate([(starch, 0.2), (flour, 0.75), (gum, 0.05)])
        assert props.viscosity_index > 1.0

    def test_hydrocolloid_pct(self):
        gum = Ingredient(name="Psyllium", category="hydrocolloid")
        flour = Ingredient(name="Rice", category="flour")
        calc = BlendCalculator()
        props = calc.calculate([(gum, 0.05), (flour, 0.95)])
        assert abs(props.hydrocolloid_pct - 0.05) < 1e-6

    def test_nutritional_computation(self):
        i1 = Ingredient(
            name="Rice",
            category="flour",
            protein_pct=6.0,
            starch_pct=80.0,
            fat_pct=1.0,
            fiber_pct=2.0,
            kcal_per_100g=366.0,
            sugars_pct=0.1,
            saturated_fat_pct=0.4,
            sodium_mg_per_100g=0.0,
        )
        i2 = Ingredient(
            name="Almond",
            category="flour",
            protein_pct=21.2,
            starch_pct=20.0,
            fat_pct=49.5,
            fiber_pct=12.5,
            kcal_per_100g=579.0,
            sugars_pct=4.4,
            saturated_fat_pct=3.8,
            sodium_mg_per_100g=1.0,
        )

        calc = BlendCalculator()
        props = calc.calculate([(i1, 0.7), (i2, 0.3)])

        assert abs(props.kcal_per_100g - (366.0 * 0.7 + 579.0 * 0.3)) < 1e-6
        assert abs(props.sugars_pct - (0.1 * 0.7 + 4.4 * 0.3)) < 1e-6
        assert abs(props.saturated_fat_pct - (0.4 * 0.7 + 3.8 * 0.3)) < 1e-6
        assert abs(props.sodium_mg_per_100g - (0.0 * 0.7 + 1.0 * 0.3)) < 1e-6

    def test_nutritional_defaults_when_missing(self):
        ing = Ingredient(
            name="Rice",
            category="flour",
            protein_pct=6.0,
        )
        calc = BlendCalculator()
        props = calc.calculate([(ing, 1.0)])
        assert props.kcal_per_100g == 0.0
        assert props.sugars_pct == 0.0
        assert props.saturated_fat_pct == 0.0
        assert props.sodium_mg_per_100g == 0.0


class TestFermentationSimulator:
    def test_simulate_returns_result(self):
        sim = FermentationSimulator()
        result = sim.simulate(viscosity_index=1.5)
        assert isinstance(result, FermentationResult)
        assert len(result.time_min) > 0
        assert len(result.volume) == len(result.time_min)

    def test_volume_increases(self):
        sim = FermentationSimulator()
        result = sim.simulate(viscosity_index=2.0)
        assert result.volume[-1] > result.volume[0]
        assert result.final_volume_increase > 0

    def test_higher_viscosity_more_retention(self):
        sim = FermentationSimulator()
        low_visc = sim.simulate(viscosity_index=0.5)
        high_visc = sim.simulate(viscosity_index=3.0)
        assert high_visc.final_volume_increase > low_visc.final_volume_increase

    def test_sugar_consumed(self):
        sim = FermentationSimulator()
        result = sim.simulate(duration_min=180.0)
        assert result.sugar[-1] < result.sugar[0]

    def test_temperature_effect(self):
        params_cold = FermentationParams(temp_c=20.0)
        params_hot = FermentationParams(temp_c=35.0)
        cold = FermentationSimulator(params_cold).simulate()
        hot = FermentationSimulator(params_hot).simulate()
        assert hot.final_volume_increase > cold.final_volume_increase

    def test_sugar_non_negative(self):
        result = FermentationSimulator().simulate(duration_min=1000.0)
        assert np.all(result.sugar >= 0.0)

    def test_rejects_invalid_yield_coeff(self):
        import pytest

        with pytest.raises(ValueError):
            FermentationSimulator(FermentationParams(yield_coeff=0.0)).simulate()
        with pytest.raises(ValueError):
            FermentationSimulator(FermentationParams(yield_coeff=-1.0)).simulate()

    def test_rejects_invalid_initial_sugar(self):
        import pytest

        with pytest.raises(ValueError):
            FermentationSimulator(
                FermentationParams(initial_sugar=-1.0)
            ).simulate()

    def test_rejects_invalid_km(self):
        import pytest

        with pytest.raises(ValueError):
            FermentationSimulator(FermentationParams(Km=0.0)).simulate()

    def test_rejects_invalid_yeast_conc(self):
        import pytest

        with pytest.raises(ValueError):
            FermentationSimulator(
                FermentationParams(yeast_conc=-1.0)
            ).simulate()


class TestBakingSimulator:
    def test_simulate_returns_result(self):
        sim = BakingSimulator()
        result = sim.simulate()
        assert result.temperature.shape[0] > 0
        assert result.temperature.shape[1] > 0

    def test_temperature_increases_at_surface(self):
        sim = BakingSimulator()
        result = sim.simulate()
        assert result.temperature[-1, 0] > result.temperature[0, 0]

    def test_core_colder_than_crust(self):
        sim = BakingSimulator()
        result = sim.simulate()
        assert result.core_temp_c < result.crust_temp_c

    def test_gelatinization_at_surface(self):
        sim = BakingSimulator()
        result = sim.simulate(gelatinization_temp_min=60.0)
        assert np.any(result.gelatinization[-1, :3] > 0.5)

    def test_surface_exceeds_90c(self):
        sim = BakingSimulator()
        result = sim.simulate()
        assert result.crust_temp_c > 90.0

    def test_core_stays_below_100c_short_bake(self):
        params = BakingParams(baking_time_min=10.0, dough_thickness_cm=3.0)
        sim = BakingSimulator(params)
        result = sim.simulate()
        assert result.core_temp_c < 100.0


class TestPastaCookingSimulator:
    def test_simulate_returns_result(self):
        props = BlendProperties(
            protein_pct=8.0,
            starch_pct=72.0,
            water_absorption=1.3,
            amylose_pct=22.0,
            hydrocolloid_pct=0.015,
        )
        result = PastaCookingSimulator().simulate(props)
        assert isinstance(result, PastaCookingResult)
        assert result.core_temp_c > 20
        assert result.water_uptake_pct > 0
        assert result.cooking_loss_pct > 0
        assert result.swelling_index > 0
        assert 0 <= result.quality_score <= 1
        assert 0 <= result.gelation_index <= 1.6
        assert 0 <= result.pregelatinization_index <= 1.0
        assert 0 <= result.syneresis_index <= 1.4
        assert 0 <= result.starch_leaching_index <= 1.4
        assert result.process_family == "generic_fresh"
        assert result.calibration_confidence == "low"
        assert 0 <= result.calibration_score <= 1
        assert result.calibration_notes

    def test_overcooking_increases_loss(self):
        props = BlendProperties(
            protein_pct=8.0,
            starch_pct=72.0,
            water_absorption=1.3,
            amylose_pct=22.0,
            hydrocolloid_pct=0.015,
        )
        short = PastaCookingSimulator(
            PastaCookingParams(cooking_time_min=4.0)
        ).simulate(props)
        long = PastaCookingSimulator(
            PastaCookingParams(cooking_time_min=14.0)
        ).simulate(props)
        assert long.cooking_loss_pct > short.cooking_loss_pct
        assert long.stickiness_index >= short.stickiness_index

    def test_hydrocolloid_reduces_cooking_loss(self):
        weak = BlendProperties(
            protein_pct=4.0,
            starch_pct=85.0,
            water_absorption=1.0,
            amylose_pct=15.0,
            hydrocolloid_pct=0.0,
        )
        structured = BlendProperties(
            protein_pct=8.0,
            starch_pct=70.0,
            water_absorption=1.4,
            amylose_pct=24.0,
            hydrocolloid_pct=0.02,
        )
        sim = PastaCookingSimulator()
        assert sim.simulate(structured).cooking_loss_pct < sim.simulate(weak).cooking_loss_pct

    def test_calcium_alginate_gelation_reduces_cooking_loss(self):
        props = BlendProperties(
            protein_pct=13.0,
            starch_pct=62.0,
            water_absorption=2.0,
            gelatinization_temp_min=62.0,
            gelatinization_temp_max=68.0,
            amylose_pct=8.0,
            hydrocolloid_pct=0.015,
            ingredients_detail=[
                {"name": "Amaranth flour", "proportion": 0.985, "category": "flour"},
                {"name": "Sodium alginate", "proportion": 0.015, "category": "hydrocolloid"},
            ],
        )
        no_calcium = PastaCookingSimulator(
            PastaCookingParams(water_to_flour_ratio=6.0, cooking_time_min=10.0)
        ).simulate(props)
        calcium = PastaCookingSimulator(
            PastaCookingParams(
                water_to_flour_ratio=6.0,
                cooking_time_min=10.0,
                calcium_lactate_m=0.1,
                calcium_bath_time_min=30.0,
            )
        ).simulate(props)

        assert calcium.gelation_index > no_calcium.gelation_index
        assert calcium.cooking_loss_pct < no_calcium.cooking_loss_pct
        assert calcium.process_family == "fresh_calcium_gel"
        assert calcium.calibration_confidence == "high"

    def test_pregelatinization_reduces_starch_leaching(self):
        props = BlendProperties(
            protein_pct=13.0,
            starch_pct=62.0,
            water_absorption=2.0,
            gelatinization_temp_min=62.0,
            gelatinization_temp_max=68.0,
            amylose_pct=8.0,
            hydrocolloid_pct=0.01,
        )
        raw = PastaCookingSimulator(
            PastaCookingParams(water_to_flour_ratio=4.0, cooking_time_min=10.0)
        ).simulate(props)
        heated = PastaCookingSimulator(
            PastaCookingParams(
                water_to_flour_ratio=4.0,
                cooking_time_min=10.0,
                dough_heat_temp_c=80.0,
                dough_heat_time_min=60.0,
            )
        ).simulate(props)

        assert heated.pregelatinization_index > raw.pregelatinization_index
        assert heated.starch_leaching_index < raw.starch_leaching_index

    def test_high_water_alginate_process_can_show_syneresis(self):
        props = BlendProperties(
            protein_pct=13.0,
            starch_pct=62.0,
            water_absorption=2.0,
            gelatinization_temp_min=62.0,
            gelatinization_temp_max=68.0,
            amylose_pct=8.0,
            hydrocolloid_pct=0.015,
            ingredients_detail=[
                {"name": "Amaranth flour", "proportion": 0.985, "category": "flour"},
                {"name": "Sodium alginate", "proportion": 0.015, "category": "hydrocolloid"},
            ],
        )
        low_water = PastaCookingSimulator(
            PastaCookingParams(
                water_to_flour_ratio=2.0,
                cooking_time_min=10.0,
                calcium_lactate_m=0.1,
                calcium_bath_time_min=30.0,
            )
        ).simulate(props)
        high_water = PastaCookingSimulator(
            PastaCookingParams(
                water_to_flour_ratio=10.0,
                cooking_time_min=10.0,
                calcium_lactate_m=0.1,
                calcium_bath_time_min=30.0,
            )
        ).simulate(props)

        assert high_water.syneresis_index > low_water.syneresis_index
        assert high_water.water_uptake_pct < low_water.water_uptake_pct

    def test_dried_rice_pasta_kgm_curdlan_effects(self):
        rf = BlendProperties(
            protein_pct=7.0,
            starch_pct=78.16,
            water_absorption=1.3,
            gelatinization_temp_min=70.55,
            gelatinization_temp_max=79.12,
            amylose_pct=28.12,
            hydrocolloid_pct=0.0,
            ingredients_detail=[
                {"name": "High-amylose rice flour", "proportion": 1.0, "category": "flour"},
            ],
        )
        kgm = BlendProperties(
            protein_pct=6.7,
            starch_pct=74.66,
            water_absorption=2.8,
            gelatinization_temp_min=70.55,
            gelatinization_temp_max=79.12,
            amylose_pct=28.12,
            hydrocolloid_pct=0.045,
            ingredients_detail=[
                {"name": "High-amylose rice flour", "proportion": 0.955, "category": "flour"},
                {"name": "Konjac glucomannan", "proportion": 0.045, "category": "hydrocolloid"},
            ],
        )
        kgm_curdlan = BlendProperties(
            protein_pct=6.5,
            starch_pct=73.0,
            water_absorption=3.2,
            gelatinization_temp_min=70.55,
            gelatinization_temp_max=79.12,
            amylose_pct=28.12,
            hydrocolloid_pct=0.066,
            ingredients_detail=[
                {"name": "High-amylose rice flour", "proportion": 0.934, "category": "flour"},
                {"name": "Konjac glucomannan", "proportion": 0.044, "category": "hydrocolloid"},
                {"name": "Curdlan", "proportion": 0.022, "category": "hydrocolloid"},
            ],
        )
        params = PastaCookingParams(dried_pasta=True, extrusion_moisture_pct=32.0)
        rf_result = PastaCookingSimulator(params).simulate(rf)
        kgm_result = PastaCookingSimulator(params).simulate(kgm)
        curdlan_result = PastaCookingSimulator(params).simulate(kgm_curdlan)

        assert kgm_result.water_uptake_pct > rf_result.water_uptake_pct
        assert kgm_result.cooking_loss_pct > rf_result.cooking_loss_pct
        assert curdlan_result.cooking_loss_pct < kgm_result.cooking_loss_pct
        assert kgm_result.process_family == "dried_extruded"
        assert kgm_result.calibration_confidence == "medium"

    def test_rejects_invalid_params(self):
        import pytest

        props = BlendProperties()
        with pytest.raises(ValueError):
            PastaCookingSimulator(PastaCookingParams(cooking_time_min=0)).simulate(props)
        with pytest.raises(ValueError):
            PastaCookingSimulator(PastaCookingParams(pasta_thickness_mm=0)).simulate(props)
        with pytest.raises(ValueError):
            PastaCookingSimulator(PastaCookingParams(water_to_flour_ratio=0)).simulate(props)
        with pytest.raises(ValueError):
            PastaCookingSimulator(PastaCookingParams(calcium_lactate_m=-0.1)).simulate(props)
        with pytest.raises(ValueError):
            PastaCookingSimulator(PastaCookingParams(extrusion_moisture_pct=0)).simulate(props)


class TestBreadQualitySimulator:
    def test_simulate_returns_bread_quality_result(self):
        props = BlendProperties(
            protein_pct=8.0,
            starch_pct=75.0,
            water_absorption=1.5,
            viscosity_index=2.0,
            hydrocolloid_pct=0.025,
            amylose_pct=22.0,
        )

        result = BreadQualitySimulator().simulate(props)

        assert result.specific_volume_cm3_g > 0
        assert result.crumb_hardness_n > 0
        assert result.porosity_pct > 0
        assert 0 <= result.moisture_retention_index <= 1
        assert result.process_family == "generic_gluten_free_bread"
        assert result.calibration_confidence == "low"

    def test_commercial_mix_has_medium_confidence(self):
        props = BlendProperties(
            protein_pct=6.5,
            starch_pct=78.0,
            water_absorption=1.7,
            viscosity_index=1.4,
            hydrocolloid_pct=0.01,
            amylose_pct=22.0,
            ingredients_detail=[
                {"name": "Commercial gluten-free bread mix", "proportion": 1.0, "category": "flour"},
            ],
        )

        result = BreadQualitySimulator(BreadQualityParams(chemical_leavening_pct=1.7)).simulate(props)

        assert result.process_family == "commercial_mix_bread"
        assert result.calibration_confidence == "medium"

    def test_hydrocolloid_bread_has_medium_confidence(self):
        props = BlendProperties(
            protein_pct=8.0,
            starch_pct=75.0,
            water_absorption=1.5,
            viscosity_index=2.0,
            hydrocolloid_pct=0.02,
            amylose_pct=22.0,
            ingredients_detail=[
                {"name": "HPMC (Hydroxypropyl Methylcellulose)", "proportion": 0.02, "category": "hydrocolloid"},
            ],
        )

        result = BreadQualitySimulator().simulate(props)

        assert result.process_family == "hydrocolloid_bread"
        assert result.calibration_confidence == "medium"

    def test_rejects_invalid_params(self):
        import pytest

        props = BlendProperties()
        with pytest.raises(ValueError):
            BreadQualitySimulator(BreadQualityParams(hydration_pct=0)).simulate(props)
        with pytest.raises(ValueError):
            BreadQualitySimulator(BreadQualityParams(baking_time_min=0)).simulate(props)
