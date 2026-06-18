from dataclasses import dataclass, field

import math


@dataclass(frozen=True)
class SweepTargetProfile:
    name: str
    volume_target: float
    volume_sigma: float
    core_target_c: float | None = None
    core_offset_from_gel_max_c: float = 12.0
    core_sigma_c: float = 12.0
    crust_target_c: float = 170.0
    crust_sigma_c: float = 28.0
    efficiency_start_min: float = 120.0
    efficiency_window_min: float = 240.0
    evidence_level: str = "heuristic"
    rationale: str = "Operational target based on Glutenix physics model outputs; not experimentally calibrated."
    sources: tuple[str, ...] = ("docs/application-targets-research.md",)
    blend_ranges: dict[str, tuple[float, float, float]] = field(default_factory=dict)


def serialize_sweep_target_profile(profile: SweepTargetProfile) -> dict:
    return {
        "name": profile.name,
        "volume_target": profile.volume_target,
        "volume_sigma": profile.volume_sigma,
        "core_target_c": profile.core_target_c,
        "core_offset_from_gel_max_c": profile.core_offset_from_gel_max_c,
        "core_sigma_c": profile.core_sigma_c,
        "crust_target_c": profile.crust_target_c,
        "crust_sigma_c": profile.crust_sigma_c,
        "efficiency_start_min": profile.efficiency_start_min,
        "efficiency_window_min": profile.efficiency_window_min,
        "evidence_level": profile.evidence_level,
        "rationale": profile.rationale,
        "sources": list(profile.sources),
        "blend_ranges": {
            key: {"min": value[0], "max": value[1], "weight": value[2]}
            for key, value in profile.blend_ranges.items()
        },
    }


def _range_score(value: float, min_value: float, max_value: float) -> float:
    width = max(max_value - min_value, 1e-6)
    target = (min_value + max_value) / 2.0
    sigma = width / 2.0
    return math.exp(-0.5 * ((value - target) / sigma) ** 2)


def score_blend_against_profile(values: dict[str, float], profile: SweepTargetProfile) -> float:
    if not profile.blend_ranges:
        return 1.0

    weighted = 0.0
    total_weight = 0.0
    for metric, (min_value, max_value, weight) in profile.blend_ranges.items():
        if metric not in values:
            continue
        weighted += weight * _range_score(values[metric], min_value, max_value)
        total_weight += weight

    if total_weight <= 0:
        return 1.0
    return weighted / total_weight


DEFAULT_SWEEP_PROFILE = SweepTargetProfile(
    name="Generico",
    volume_target=0.70,
    volume_sigma=0.25,
    core_target_c=None,
    core_offset_from_gel_max_c=12.0,
    core_sigma_c=12.0,
    crust_target_c=170.0,
    crust_sigma_c=28.0,
    efficiency_start_min=120.0,
    efficiency_window_min=240.0,
    rationale="Fallback profile for process exploration when no product application is selected.",
    sources=("docs/application-targets-research.md#metriche-target",),
    blend_ranges={},
)


SWEEP_TARGET_PROFILES = {
    "pizza": SweepTargetProfile(
        name="Pizza",
        volume_target=0.65,
        volume_sigma=0.20,
        core_target_c=94.0,
        core_sigma_c=8.0,
        crust_target_c=205.0,
        crust_sigma_c=30.0,
        efficiency_start_min=150.0,
        efficiency_window_min=240.0,
        rationale="Prioritizes cooked structure and hotter crust for pizza-style browning; volume is useful but not maximized at bread-like levels.",
        sources=(
            "docs/application-targets-research.md#pizza-gluten-free",
            "docs/application-targets-research.md#fonti-verificate-e-dati-estratti",
        ),
        blend_ranges={
            "water_absorption": (1.2, 1.9, 1.0),
            "viscosity_index": (1.4, 2.8, 1.0),
            "hydrocolloid_pct": (0.01, 0.04, 1.2),
            "fiber_pct": (2.0, 8.0, 0.6),
            "fat_pct": (0.5, 6.0, 0.5),
        },
    ),
    "pane": SweepTargetProfile(
        name="Pane",
        volume_target=0.90,
        volume_sigma=0.25,
        core_target_c=96.0,
        core_sigma_c=7.0,
        crust_target_c=175.0,
        crust_sigma_c=25.0,
        efficiency_start_min=170.0,
        efficiency_window_min=260.0,
        rationale="Prioritizes high loaf expansion, complete crumb bake near 96C, and moderate crust browning for bread.",
        sources=(
            "docs/application-targets-research.md#pane-gluten-free",
            "docs/application-targets-research.md#fonti-verificate-e-dati-estratti",
        ),
        blend_ranges={
            "water_absorption": (1.4, 2.2, 1.0),
            "viscosity_index": (1.8, 3.5, 1.0),
            "hydrocolloid_pct": (0.015, 0.05, 1.2),
            "fiber_pct": (3.0, 10.0, 0.7),
            "protein_pct": (5.0, 12.0, 0.6),
        },
    ),
    "lievitati dolci": SweepTargetProfile(
        name="Lievitati dolci",
        volume_target=0.95,
        volume_sigma=0.30,
        core_target_c=94.0,
        core_sigma_c=8.0,
        crust_target_c=165.0,
        crust_sigma_c=24.0,
        efficiency_start_min=180.0,
        efficiency_window_min=300.0,
        rationale="Targets high expansion and gentle crust for enriched sweet doughs where softness is preferred over aggressive browning.",
        sources=(
            "docs/application-targets-research.md#lievitati-dolci-gluten-free",
            "docs/application-targets-research.md#fonti-verificate-e-dati-estratti",
        ),
        blend_ranges={
            "water_absorption": (1.3, 2.1, 1.0),
            "viscosity_index": (1.6, 3.2, 1.0),
            "hydrocolloid_pct": (0.01, 0.045, 1.2),
            "fat_pct": (3.0, 15.0, 0.6),
            "fiber_pct": (2.0, 8.0, 0.5),
        },
    ),
    "frolla": SweepTargetProfile(
        name="Frolla",
        volume_target=0.08,
        volume_sigma=0.12,
        core_target_c=88.0,
        core_sigma_c=12.0,
        crust_target_c=165.0,
        crust_sigma_c=22.0,
        efficiency_start_min=55.0,
        efficiency_window_min=120.0,
        rationale="Penalizes volume development and long fermentation because shortcrust/frolla should hold shape and remain friable.",
        sources=(
            "docs/application-targets-research.md#crostata--frolla-gluten-free",
            "docs/application-targets-research.md#fonti-verificate-e-dati-estratti",
        ),
        blend_ranges={
            "water_absorption": (0.7, 1.3, 1.0),
            "viscosity_index": (0.5, 1.2, 1.0),
            "hydrocolloid_pct": (0.0, 0.01, 1.1),
            "fat_pct": (8.0, 30.0, 0.8),
            "starch_pct": (45.0, 75.0, 0.6),
        },
    ),
    "pasta fresca": SweepTargetProfile(
        name="Pasta fresca",
        volume_target=0.00,
        volume_sigma=0.10,
        core_target_c=80.0,
        core_sigma_c=10.0,
        crust_target_c=100.0,
        crust_sigma_c=30.0,
        efficiency_start_min=30.0,
        efficiency_window_min=90.0,
        rationale="Process profile placeholder for pasta-style heat treatment; low volume is preferred and crust is not a target in normal pasta cooking.",
        sources=(
            "docs/application-targets-research.md#pasta-fresca-gluten-free",
            "docs/application-targets-research.md#fonti-verificate-e-dati-estratti",
        ),
        blend_ranges={
            "water_absorption": (0.9, 1.6, 1.0),
            "viscosity_index": (1.2, 2.5, 1.0),
            "hydrocolloid_pct": (0.005, 0.03, 1.0),
            "protein_pct": (7.0, 15.0, 0.7),
            "amylose_pct": (15.0, 30.0, 0.7),
        },
    ),
    "biscotti": SweepTargetProfile(
        name="Biscotti",
        volume_target=0.12,
        volume_sigma=0.15,
        core_target_c=90.0,
        core_sigma_c=12.0,
        crust_target_c=170.0,
        crust_sigma_c=24.0,
        efficiency_start_min=60.0,
        efficiency_window_min=140.0,
        rationale="Targets low expansion with enough core heating and crust browning for crisp biscuit/cookie texture.",
        sources=(
            "docs/application-targets-research.md#biscotti-gluten-free",
            "docs/application-targets-research.md#fonti-verificate-e-dati-estratti",
        ),
        blend_ranges={
            "water_absorption": (0.7, 1.4, 1.0),
            "viscosity_index": (0.5, 1.4, 1.0),
            "hydrocolloid_pct": (0.0, 0.015, 1.1),
            "fat_pct": (5.0, 25.0, 0.8),
            "starch_pct": (45.0, 80.0, 0.6),
        },
    ),
}


def get_sweep_target_profile(application_name: str | None) -> SweepTargetProfile:
    if not application_name:
        return DEFAULT_SWEEP_PROFILE
    return SWEEP_TARGET_PROFILES.get(
        application_name.strip().lower(),
        DEFAULT_SWEEP_PROFILE,
    )
