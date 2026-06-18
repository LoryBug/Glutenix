from dataclasses import dataclass


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
    ),
}


def get_sweep_target_profile(application_name: str | None) -> SweepTargetProfile:
    if not application_name:
        return DEFAULT_SWEEP_PROFILE
    return SWEEP_TARGET_PROFILES.get(
        application_name.strip().lower(),
        DEFAULT_SWEEP_PROFILE,
    )
