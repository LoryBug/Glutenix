from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp


@dataclass
class FermentationParams:
    Vmax: float = 0.025
    Km: float = 0.5
    Ea: float = 50_000
    R: float = 8.314
    T_ref: float = 303.15
    yeast_conc: float = 1.0
    initial_sugar: float = 5.0
    yield_coeff: float = 0.5

    temp_c: float = 30.0

    eta_factor: float = 0.3

    @property
    def temp_k(self) -> float:
        return self.temp_c + 273.15


@dataclass
class FermentationResult:
    time_min: np.ndarray
    volume: np.ndarray
    co2_produced: np.ndarray
    co2_trapped: np.ndarray
    sugar: np.ndarray
    final_volume_increase: float


class FermentationSimulator:
    def __init__(self, params: FermentationParams | None = None):
        self.params = params or FermentationParams()

    def simulate(
        self,
        viscosity_index: float = 1.0,
        duration_min: float = 120.0,
        n_points: int = 200,
    ) -> FermentationResult:
        p = self.params

        if p.yield_coeff <= 0:
            raise ValueError(
                f"yield_coeff must be positive, got {p.yield_coeff}"
            )
        if p.Km <= 0:
            raise ValueError(f"Km must be positive, got {p.Km}")
        if p.initial_sugar < 0:
            raise ValueError(
                f"initial_sugar must be non-negative, got {p.initial_sugar}"
            )
        if p.yeast_conc < 0:
            raise ValueError(
                f"yeast_conc must be non-negative, got {p.yeast_conc}"
            )

        def ode(t, y):
            co2, S = y
            S = max(S, 0.0)
            arrhenius = np.exp(
                -p.Ea / p.R * (1.0 / p.temp_k - 1.0 / p.T_ref)
            )
            dco2 = p.Vmax * S / (p.Km + S) * arrhenius * p.yeast_conc
            dS = -(1.0 / p.yield_coeff) * dco2
            return [dco2, dS]

        t_span = (0.0, duration_min)
        y0 = [0.0, p.initial_sugar]
        t_eval = np.linspace(0, duration_min, n_points)

        sol = solve_ivp(
            ode,
            t_span,
            y0,
            t_eval=t_eval,
            method="RK45",
            rtol=1e-6,
            atol=1e-9,
        )

        if not sol.success:
            raise RuntimeError(
                f"Fermentation solver failed: {sol.message}"
            )

        co2_produced = np.minimum(
            sol.y[0], p.initial_sugar * p.yield_coeff
        )
        sugar = np.maximum(sol.y[1], 0.0)

        retention = 1.0 - 0.3 * np.exp(-viscosity_index * 0.5)
        co2_trapped = co2_produced * retention

        volume = 1.0 + p.eta_factor * co2_trapped
        final_increase = float(volume[-1] - 1.0)

        return FermentationResult(
            time_min=sol.t,
            volume=volume,
            co2_produced=co2_produced,
            co2_trapped=co2_trapped,
            sugar=sugar,
            final_volume_increase=final_increase,
        )
