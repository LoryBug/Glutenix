import pytest
import torch

from glutenix.bo.explain import ard_feature_importance, partial_dependence
from glutenix.bo.optimizer import BayesianOptimizer
from glutenix.ml.gpr import PhysicsGPR


@pytest.fixture
def trained_gpr():
    torch.manual_seed(42)
    x = torch.randn(30, 9)
    y = x[:, 0] * 0.5 + x[:, 1] * 0.3 + torch.randn(30) * 0.1
    gpr = PhysicsGPR()
    gpr.train(x, y, n_iter=30, verbose=False)
    return gpr, x


class TestARD:
    def test_returns_dict(self, trained_gpr):
        gpr, _ = trained_gpr
        imp = ard_feature_importance(gpr)
        assert isinstance(imp, dict)
        assert len(imp) == 9
        for name in gpr.FEATURE_NAMES:
            assert name in imp
            assert imp[name] > 0

    def test_untrained_raises(self):
        with pytest.raises(RuntimeError, match="not trained"):
            ard_feature_importance(PhysicsGPR())


class TestPartialDependence:
    def test_returns_correct_shapes(self, trained_gpr):
        gpr, train_x = trained_gpr
        grid, means, stds = partial_dependence(gpr, train_x, 0)
        assert grid.shape[0] == 50
        assert means.shape == (50,)
        assert stds.shape == (50,)

    def test_untrained_raises(self, trained_gpr):
        _, train_x = trained_gpr
        with pytest.raises(RuntimeError, match="not trained"):
            partial_dependence(PhysicsGPR(), train_x, 0)

    def test_invalid_feature_raises(self, trained_gpr):
        gpr, train_x = trained_gpr
        with pytest.raises(ValueError, match="out of range"):
            partial_dependence(gpr, train_x, 99)


class TestBayesianOptimizer:
    def test_initial_suggest_sobol(self):
        bounds = torch.tensor([[0.0, 0.0], [1.0, 1.0]], dtype=torch.float)
        opt = BayesianOptimizer(
            feature_names=["a", "b"],
            bounds=bounds,
            objective_names=["score"],
        )
        cand = opt.suggest(n_candidates=2)
        assert cand.shape == (2, 2)
        assert (cand >= 0).all() and (cand <= 1).all()

    def test_single_objective(self):
        bounds = torch.tensor([[0.0, 0.0], [1.0, 1.0]], dtype=torch.float)
        opt = BayesianOptimizer(
            feature_names=["a", "b"],
            bounds=bounds,
            objective_names=["score"],
        )
        for _ in range(5):
            x = torch.rand(1, 2)
            y = (x[:, 0:1] + x[:, 1:2]) * 0.5
            opt.register_evaluation(x, y)
        cand = opt.suggest(n_candidates=1)
        assert cand.shape == (1, 2)

    def test_multi_objective(self):
        bounds = torch.tensor([[0.0, 0.0], [1.0, 1.0]], dtype=torch.float)
        opt = BayesianOptimizer(
            feature_names=["a", "b"],
            bounds=bounds,
            objective_names=["v1", "v2"],
        )
        for _ in range(5):
            x = torch.rand(1, 2)
            y = torch.cat([x[:, 0:1] * 0.5, x[:, 1:2] * 0.3], dim=1)
            opt.register_evaluation(x, y)
        cand = opt.suggest(n_candidates=1)
        assert cand.shape == (1, 2)

    def test_no_evaluations_suggest(self):
        bounds = torch.tensor([[0.0], [1.0]], dtype=torch.float)
        opt = BayesianOptimizer(
            feature_names=["x"],
            bounds=bounds,
            objective_names=["score"],
        )
        cand = opt.suggest(n_candidates=3)
        assert cand.shape == (3, 1)
