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
    latent_heat: float = 2.26e6
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

        dx = p.dough_thickness_cm / (p.n_spatial - 1)

        alpha = p.thermal_diffusivity
        dt_max = 0.4 * dx**2 / alpha
        dt_suggested = p.baking_time_min * 60.0 / p.n_time

        if dt_suggested > dt_max:
            n_time = int(np.ceil(p.baking_time_min * 60.0 / dt_max))
        else:
            n_time = p.n_time

        dt = p.baking_time_min * 60.0 / n_time

        x = np.linspace(0, p.dough_thickness_cm, p.n_spatial)
        t = np.linspace(0, p.baking_time_min * 60.0, n_time)

        T = np.full((n_time, p.n_spatial), T0)

        r = alpha * dt / dx**2
        h = p.surface_heat_transfer
        rho_cp = p.density * p.specific_heat

        for n in range(n_time - 1):
            T_curr = T[n]
            T_next = T_curr.copy()

            T_next[1:-1] += r * (
                T_curr[2:] - 2 * T_curr[1:-1] + T_curr[:-2]
            )

            T_next[0] += r * 2 * (T_curr[1] - T_curr[0])
            T_next[0] += dt * h * (T_oven - T_curr[0]) / rho_cp / dx

            T_next[-1] += r * 2 * (T_curr[-2] - T_curr[-1])

            T[n + 1] = T_next

        G = np.clip(
            (T - T_gel_min) / (T_gel_max - T_gel_min),
            0,
            1,
        )

        M = np.zeros(n_time)
        for n in range(1, n_time):
            T_surface = T[n, 0]
            if T_surface > 373.15:
                T_c = T_surface - 273.15
                M[n] = M[n - 1] + dt * 1e-4 * np.exp(-8000.0 / (T_c + 200.0))
        M_norm = M / (np.max(M) + 1e-10)

        return BakingResult(
            time_min=t / 60.0,
            position_cm=x,
            temperature=T - 273.15,
            gelatinization=G,
            maillard_index=M_norm,
            core_temp_c=float(T[-1, -1] - 273.15),
            crust_temp_c=float(T[-1, 0] - 273.15),
        )
