import numpy as np

from glutenix.db.models import Ingredient
from glutenix.engine.baking import BakingParams, BakingSimulator
from glutenix.engine.blend import BlendCalculator, BlendProperties
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
