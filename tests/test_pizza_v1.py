from glutenix.calibration.pizza_v1 import assess_pizza_v1_coverage


def test_pizza_v1_coverage_passes_audited_boundary_point():
    diagnostics = assess_pizza_v1_coverage(
        ingredient_names=[
            "White rice flour",
            "Sorghum flour",
            "Tapioca starch",
            "Psyllium husk",
        ],
        blend_values={
            "water_absorption": 1.5,
            "viscosity_index": 2.0,
            "hydrocolloid_pct": 0.018,
            "fiber_pct": 4.0,
            "fat_pct": 2.0,
        },
        process_values={
            "fermentation_temp_c": 37.0,
            "fermentation_duration_min": 120.0,
            "baking_temp_c": 204.4,
            "baking_duration_min": 10.0,
        },
    )

    assert diagnostics.coverage_fraction == 1.0
    assert diagnostics.warning is False
    assert diagnostics.risk_flags == []
    assert all(item.status == "in_range" for item in diagnostics.variable_diagnostics)


def test_pizza_v1_coverage_flags_out_of_range_process():
    diagnostics = assess_pizza_v1_coverage(
        ingredient_names=["White rice flour", "Unknown flour"],
        blend_values={
            "water_absorption": 2.5,
            "viscosity_index": 2.0,
            "hydrocolloid_pct": 0.06,
            "fiber_pct": 4.0,
            "fat_pct": 2.0,
        },
        process_values={
            "fermentation_temp_c": 25.0,
            "fermentation_duration_min": 480.0,
            "baking_temp_c": 450.0,
            "baking_duration_min": 2.0,
        },
    )

    assert diagnostics.coverage_fraction < 0.5
    assert diagnostics.warning is True
    assert "ingredient:Unknown flour" in diagnostics.unsupported_variables
    assert "baking_temp_c" in diagnostics.unsupported_variables
    assert any("below 0.5" in flag for flag in diagnostics.risk_flags)


def test_pizza_v1_literature_proxy_is_low_when_coverage_is_low():
    diagnostics = assess_pizza_v1_coverage(
        ingredient_names=["Unknown flour"],
        blend_values={},
        process_values={},
    )

    proxy = diagnostics.as_literature_coverage()

    assert proxy["level"] == "low"
    assert proxy["calibration_coverage"] == 0.0
    assert proxy["risk_flags"]
