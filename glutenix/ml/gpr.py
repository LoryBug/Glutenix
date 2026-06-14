from dataclasses import dataclass

import gpytorch
import torch
from gpytorch.distributions import MultivariateNormal
from gpytorch.kernels import RBFKernel, ScaleKernel
from gpytorch.means import ConstantMean
from gpytorch.models import ExactGP


class PhysicsKernel(gpytorch.kernels.Kernel):
    def __init__(self, n_features: int = 9):
        super().__init__()
        self.base_kernel = ScaleKernel(RBFKernel(ard_num_dims=n_features))

    def forward(self, x1, x2, diag=False, **params):
        return self.base_kernel.forward(x1, x2, diag=diag, **params)


class PhysicsGPModel(ExactGP):
    def __init__(
        self,
        train_x: torch.Tensor,
        train_y: torch.Tensor,
        likelihood: gpytorch.likelihoods.Likelihood,
    ):
        super().__init__(train_x, train_y, likelihood)
        self.mean_module = ConstantMean()
        self.covar_module = PhysicsKernel(n_features=train_x.shape[-1])

    def forward(self, x: torch.Tensor) -> MultivariateNormal:
        mean = self.mean_module(x)
        covar = self.covar_module(x)
        return MultivariateNormal(mean, covar)


@dataclass
class Prediction:
    mean: float
    std: float
    conf_interval_95: tuple[float, float]


class PhysicsGPR:
    FEATURE_NAMES = [
        "protein_pct",
        "starch_pct",
        "fat_pct",
        "fiber_pct",
        "water_absorption",
        "gelatinization_temp_min",
        "amylose_pct",
        "viscosity_index",
        "hydrocolloid_pct",
    ]

    def __init__(self):
        self.model: PhysicsGPModel | None = None
        self.likelihood: gpytorch.likelihoods.GaussianLikelihood | None = None

    @property
    def is_trained(self) -> bool:
        return self.model is not None

    def _normalize(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        mean = x.mean(0)
        std = x.std(0, unbiased=False).clamp(min=1e-8)
        return (x - mean) / std, mean, std

    def train(
        self,
        train_x: torch.Tensor,
        train_y: torch.Tensor,
        n_iter: int = 200,
        lr: float = 0.1,
        verbose: bool = True,
    ):
        x_norm, x_mean, x_std = self._normalize(train_x)
        y_mean = train_y.mean()
        y_std = train_y.std(unbiased=False).clamp(min=1e-8)
        y_norm = (train_y - y_mean) / y_std

        self._x_mean = x_mean
        self._x_std = x_std
        self._y_mean = y_mean
        self._y_std = y_std

        self.likelihood = gpytorch.likelihoods.GaussianLikelihood()
        self.model = PhysicsGPModel(x_norm, y_norm, self.likelihood)

        self.model.train()
        self.likelihood.train()

        optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=lr,
        )

        mll = gpytorch.mlls.ExactMarginalLogLikelihood(
            self.likelihood, self.model
        )

        for i in range(n_iter):
            optimizer.zero_grad()
            output = self.model(x_norm)
            loss = -mll(output, y_norm)
            loss.backward()
            optimizer.step()

            if verbose and (i + 1) % 50 == 0:
                print(f"Iter {i+1:3d}/{n_iter} | Loss: {loss.item():.4f}")

    def predict(self, features: list[float] | torch.Tensor) -> Prediction:
        if not self.is_trained:
            raise RuntimeError("Model not trained. Call train() first.")

        if isinstance(features, list):
            x = torch.tensor([features], dtype=torch.float)
        else:
            x = features.unsqueeze(0) if features.ndim == 1 else features

        x_norm = (x - self._x_mean) / self._x_std

        self.model.eval()
        self.likelihood.eval()

        with torch.no_grad(), gpytorch.settings.fast_pred_var():
            pred = self.likelihood(self.model(x_norm))
            mean = pred.mean * self._y_std + self._y_mean
            std = pred.stddev * self._y_std

        mean_val = float(mean.squeeze().item())
        std_val = float(std.squeeze().item())

        return Prediction(
            mean=mean_val,
            std=std_val,
            conf_interval_95=(
                round(mean_val - 1.96 * std_val, 4),
                round(mean_val + 1.96 * std_val, 4),
            ),
        )

    def predict_batch(
        self, features: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if not self.is_trained:
            raise RuntimeError("Model not trained.")

        x_norm = (features - self._x_mean) / self._x_std

        self.model.eval()
        self.likelihood.eval()

        with torch.no_grad(), gpytorch.settings.fast_pred_var():
            pred = self.likelihood(self.model(x_norm))
            mean = pred.mean * self._y_std + self._y_mean
            std = pred.stddev * self._y_std

        return mean, std

    def save(self, path: str):
        if not self.is_trained:
            raise RuntimeError("Model not trained. Nothing to save.")
        torch.save(
            {
                "model_state_dict": self.model.state_dict(),
                "likelihood_state_dict": self.likelihood.state_dict(),
                "train_x": self.model.train_inputs[0].detach().cpu(),
                "train_y": self.model.train_targets.detach().cpu(),
                "x_mean": self._x_mean,
                "x_std": self._x_std,
                "y_mean": self._y_mean,
                "y_std": self._y_std,
            },
            path,
        )

    @classmethod
    def load(cls, path: str) -> "PhysicsGPR":
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        required = {
            "model_state_dict",
            "likelihood_state_dict",
            "train_x",
            "train_y",
            "x_mean",
            "x_std",
            "y_mean",
            "y_std",
        }
        missing = required - checkpoint.keys()
        if missing:
            raise ValueError(f"Invalid checkpoint, missing keys: {missing}")

        gpr = cls()
        gpr._x_mean = checkpoint["x_mean"]
        gpr._x_std = checkpoint["x_std"]
        gpr._y_mean = checkpoint["y_mean"]
        gpr._y_std = checkpoint["y_std"]

        gpr.likelihood = gpytorch.likelihoods.GaussianLikelihood()
        gpr.model = PhysicsGPModel(checkpoint["train_x"], checkpoint["train_y"], gpr.likelihood)
        gpr.model.load_state_dict(checkpoint["model_state_dict"])
        gpr.likelihood.load_state_dict(checkpoint["likelihood_state_dict"])
        gpr.model.eval()
        gpr.likelihood.eval()
        return gpr
