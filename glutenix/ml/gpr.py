from dataclasses import dataclass, field

import gpytorch
import structlog
import torch
from gpytorch.distributions import MultivariateNormal
from gpytorch.kernels import RBFKernel, ScaleKernel
from gpytorch.means import ConstantMean
from gpytorch.models import ExactGP

logger = structlog.get_logger("glutenix.ml.gpr")


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


@dataclass
class EvalMetrics:
    rmse: float
    mae: float
    r2: float


@dataclass
class TrainHistoryEntry:
    iteration: int
    train_loss: float
    val_loss: float | None = None


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
        self.train_history: list[TrainHistoryEntry] = field(default_factory=list)
        self._best_val_loss: float = float("inf")

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
        val_split: float = 0.0,
        patience: int = 20,
        verbose: bool = True,
    ):
        n = len(train_y)
        if val_split > 0 and n > 10:
            n_val = max(1, int(n * val_split))
            perm = torch.randperm(n)
            val_idx, tr_idx = perm[:n_val], perm[n_val:]
            x_tr, y_tr = train_x[tr_idx], train_y[tr_idx]
            x_val, y_val = train_x[val_idx], train_y[val_idx]
        else:
            x_tr, y_tr = train_x, train_y
            x_val = y_val = None

        x_norm, x_mean, x_std = self._normalize(x_tr)
        y_mean = y_tr.mean()
        y_std = y_tr.std(unbiased=False).clamp(min=1e-8)
        y_norm = (y_tr - y_mean) / y_std

        self._x_mean = x_mean
        self._x_std = x_std
        self._y_mean = y_mean
        self._y_std = y_std

        self.likelihood = gpytorch.likelihoods.GaussianLikelihood()
        self.model = PhysicsGPModel(x_norm, y_norm, self.likelihood)

        self.model.train()
        self.likelihood.train()

        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=patience // 2, min_lr=1e-5
        )

        mll = gpytorch.mlls.ExactMarginalLogLikelihood(self.likelihood, self.model)
        self.train_history = []
        self._best_val_loss = float("inf")
        best_state = None
        stall = 0

        if x_val is not None:
            x_val_norm = (x_val - x_mean) / x_std
            y_val_norm = (y_val - y_mean) / y_std

        for i in range(n_iter):
            optimizer.zero_grad()
            output = self.model(x_norm)
            loss = -mll(output, y_norm)
            loss.backward()
            optimizer.step()

            if x_val is not None:
                self.model.eval()
                with torch.no_grad():
                    val_out = self.model(x_val_norm)
                    vloss = -mll(val_out, y_val_norm)
                self.model.train()
                val_loss = float(vloss.item())
                scheduler.step(val_loss)

                if val_loss < self._best_val_loss:
                    self._best_val_loss = val_loss
                    best_state = {
                        "model": self.model.state_dict(),
                        "likelihood": self.likelihood.state_dict(),
                    }
                    stall = 0
                else:
                    stall += 1

                if patience > 0 and stall >= patience:
                    logger.warning(
                        "early_stopping",
                        iteration=i + 1,
                        patience=patience,
                        best_val_loss=round(self._best_val_loss, 4),
                    )
                    if best_state is not None:
                        self.model.load_state_dict(best_state["model"])
                        self.likelihood.load_state_dict(best_state["likelihood"])
                    break
            else:
                val_loss = None

            self.train_history.append(TrainHistoryEntry(
                iteration=i + 1,
                train_loss=float(loss.item()),
                val_loss=val_loss,
            ))

            if verbose and (i + 1) % 50 == 0:
                log_data = dict(
                    iteration=i + 1,
                    n_iter=n_iter,
                    train_loss=round(loss.item(), 4),
                )
                if val_loss is not None:
                    log_data["val_loss"] = round(val_loss, 4)
                logger.info("training_iter", **log_data)

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

    def evaluate(self, eval_x: torch.Tensor, eval_y: torch.Tensor) -> EvalMetrics:
        if not self.is_trained:
            raise RuntimeError("Model not trained.")
        mean, _ = self.predict_batch(eval_x)
        rmse = float(torch.sqrt(((mean - eval_y) ** 2).mean()))
        mae = float(torch.abs(mean - eval_y).mean())
        ss_res = ((mean - eval_y) ** 2).sum()
        ss_tot = ((eval_y - eval_y.mean()) ** 2).sum()
        r2 = float(1 - ss_res / ss_tot.clamp(min=1e-12))
        return EvalMetrics(rmse=rmse, mae=mae, r2=r2)

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
                "train_history": [{"iteration": h.iteration, "train_loss": h.train_loss, "val_loss": h.val_loss} for h in self.train_history],
                "best_val_loss": self._best_val_loss,
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
        gpr.train_history = [
            TrainHistoryEntry(**h) if isinstance(h, dict) else h
            for h in checkpoint.get("train_history", [])
        ]
        gpr._best_val_loss = float(checkpoint.get("best_val_loss", float("inf")))
        gpr.model.eval()
        gpr.likelihood.eval()
        return gpr
