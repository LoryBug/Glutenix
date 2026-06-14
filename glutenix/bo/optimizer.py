import torch
from botorch.acquisition import qLogExpectedImprovement
from botorch.acquisition.multi_objective import (
    qLogNoisyExpectedHypervolumeImprovement,
)
from botorch.models import ModelListGP, SingleTaskGP
from botorch.optim import optimize_acqf
from botorch.utils.sampling import draw_sobol_samples
from torch import Tensor


class BayesianOptimizer:
    def __init__(
        self,
        feature_names: list[str],
        bounds: Tensor,
        objective_names: list[str] | None = None,
    ):
        self.feature_names = feature_names
        self.bounds = bounds
        self.objective_names = objective_names or [f"objective_{i}" for i in range(bounds.shape[1])]
        self.X: list[Tensor] = []
        self.Y: list[Tensor] = []

    @property
    def n_objectives(self) -> int:
        return len(self.objective_names)

    @property
    def n_features(self) -> int:
        return self.bounds.shape[1]

    def register_evaluation(self, x: Tensor, y: Tensor):
        self.X.append(x.double())
        self.Y.append(y.double())

    @property
    def X_tensor(self) -> Tensor | None:
        return torch.cat(self.X) if self.X else None

    @property
    def Y_tensor(self) -> Tensor | None:
        return torch.cat(self.Y) if self.Y else None

    def _build_models(self) -> ModelListGP:
        models = [
            SingleTaskGP(self.X_tensor, self.Y_tensor[:, i : i + 1])
            for i in range(self.n_objectives)
        ]
        return ModelListGP(*models)

    def suggest(
        self,
        n_candidates: int = 1,
        n_restarts: int = 5,
        raw_samples: int = 128,
    ) -> Tensor:
        bounds = self.bounds.double()
        if not self.X:
            return draw_sobol_samples(bounds=bounds, n=n_candidates, q=1).squeeze(1)

        model = self._build_models()
        Y = self.Y_tensor
        Y_best = Y.max(0).values

        if self.n_objectives == 1:
            acqf = qLogExpectedImprovement(model, best_f=Y_best[0])
        else:
            ref_point = Y.min(0).values - 0.1 * (Y.max(0).values - Y.min(0).values + 1e-10)
            acqf = qLogNoisyExpectedHypervolumeImprovement(
                model,
                ref_point=ref_point,
                X_baseline=self.X_tensor.double(),
            )

        candidates, _ = optimize_acqf(
            acq_function=acqf,
            bounds=bounds,
            q=n_candidates,
            num_restarts=n_restarts,
            raw_samples=raw_samples,
            options={"batch_limit": 5, "maxiter": 200},
        )
        return candidates
