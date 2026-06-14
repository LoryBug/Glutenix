import gpytorch
import torch

from glutenix.ml.gpr import PhysicsGPR


def ard_feature_importance(gpr: PhysicsGPR) -> dict[str, float]:
    if not gpr.is_trained:
        raise RuntimeError("Model not trained. Call train() first.")
    ls = gpr.model.covar_module.base_kernel.base_kernel.lengthscale
    inv = (1.0 / ls.squeeze()).tolist()
    return dict(zip(gpr.FEATURE_NAMES, inv))


def partial_dependence(
    gpr: PhysicsGPR,
    train_x: torch.Tensor,
    feature_idx: int,
    grid_points: int = 50,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    if not gpr.is_trained:
        raise RuntimeError("Model not trained. Call train() first.")
    if feature_idx < 0 or feature_idx >= train_x.shape[1]:
        raise ValueError(f"feature_idx {feature_idx} out of range")
    x_norm = (train_x - gpr._x_mean) / gpr._x_std
    f_min = float(x_norm[:, feature_idx].min())
    f_max = float(x_norm[:, feature_idx].max())
    grid = torch.linspace(f_min, f_max, grid_points)
    means = []
    stds = []
    for val in grid:
        x_grid = x_norm.clone()
        x_grid[:, feature_idx] = val
        gpr.model.eval()
        gpr.likelihood.eval()
        with torch.no_grad(), gpytorch.settings.fast_pred_var():
            pred = gpr.likelihood(gpr.model(x_grid))
            m = pred.mean * gpr._y_std + gpr._y_mean
            s = pred.stddev * gpr._y_std
        means.append(m.mean())
        stds.append(s.mean())
    grid_orig = grid * gpr._x_std[feature_idx] + gpr._x_mean[feature_idx]
    return (
        grid_orig,
        torch.tensor(means),
        torch.tensor(stds),
    )
