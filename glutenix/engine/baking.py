from dataclasses import dataclass

import numpy as np


@dataclass
class BakingParams:
    oven_temp_c: float = 200.0
    initial_temp_c: float = 30.0
    dough_thickness_cm: float = 3.0
    baking_time_min: float = 25.0

    thermal_diffusivity: float = 1.5e-7
    specific_heat: float = 2800.0
    density: float = 400.0
    surface_heat_transfer: float = 25.0

    n_spatial: int = 50
    n_time: int = 200


@dataclass
class BakingResult:
    time_min: np.ndarray
    position_cm: np.ndarray
    temperature: np.ndarray
    gelatinization: np.ndarray
    maillard_index: np.ndarray
    core_temp_c: float
    crust_temp_c: float


class BakingSimulator:
    def __init__(self, params: BakingParams | None = None):
        self.params = params or BakingParams()

    def simulate(
        self,
        gelatinization_temp_min: float = 62.0,
        gelatinization_temp_max: float = 78.0,
    ) -> BakingResult:
        p = self.params

        T0 = p.initial_temp_c + 273.15
        T_oven = p.oven_temp_c + 273.15
        T_gel_min = gelatinization_temp_min + 273.15
        T_gel_max = gelatinization_temp_max + 273.15

        dx_m = p.dough_thickness_cm / (p.n_spatial - 1) / 100.0

        alpha = p.thermal_diffusivity
        total_s = p.baking_time_min * 60.0
        dt_max = 0.4 * dx_m**2 / alpha
        dt_suggested = total_s / p.n_time

        if dt_suggested > dt_max:
            n_steps = int(np.ceil(total_s / dt_max))
        else:
            n_steps = p.n_time

        dt = total_s / n_steps

        x_cm = np.linspace(0, p.dough_thickness_cm, p.n_spatial)
        t = np.linspace(0, total_s, n_steps + 1)

        T = np.full((n_steps + 1, p.n_spatial), T0)

        r = alpha * dt / dx_m**2
        h = p.surface_heat_transfer
        rho_cp = p.density * p.specific_heat

        for n in range(n_steps):
            T_curr = T[n]
            T_next = T_curr.copy()

            T_next[1:-1] += r * (
                T_curr[2:] - 2 * T_curr[1:-1] + T_curr[:-2]
            )

            T_next[0] += r * 2 * (T_curr[1] - T_curr[0])
            T_next[0] += dt * 2 * h * (T_oven - T_curr[0]) / rho_cp / dx_m

            T_next[-1] += r * 2 * (T_curr[-2] - T_curr[-1])

            T[n + 1] = T_next

        gel_range = T_gel_max - T_gel_min
        if gel_range > 0:
            G = np.clip((T - T_gel_min) / gel_range, 0, 1)
        else:
            G = np.where(T >= T_gel_min, 1.0, 0.0)

        M = np.zeros(n_steps + 1)
        for n in range(1, n_steps + 1):
            T_surface = T[n, 0]
            if T_surface > 373.15:
                T_c = T_surface - 273.15
                M[n] = M[n - 1] + dt * 1e-4 * np.exp(-8000.0 / (T_c + 200.0))
        M_norm = M / (np.max(M) + 1e-10)

        return BakingResult(
            time_min=t / 60.0,
            position_cm=x_cm,
            temperature=T - 273.15,
            gelatinization=G,
            maillard_index=M_norm,
            core_temp_c=float(T[-1, -1] - 273.15),
            crust_temp_c=float(T[-1, 0] - 273.15),
        )
