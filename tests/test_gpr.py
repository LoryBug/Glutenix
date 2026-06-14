import torch

from glutenix.db.base import Base, engine, SessionLocal
from glutenix.db.models import Ingredient
from glutenix.db.seed import seed_database
from glutenix.ml.gpr import PhysicsGPR
from glutenix.ml.train import generate_synthetic_data


def test_gpr_training():
    Base.metadata.create_all(engine)
    seed_database()

    session = SessionLocal()
    ingredients = session.query(Ingredient).all()
    session.close()

    train_x, train_y = generate_synthetic_data(ingredients, n_samples=300)
    train_y += torch.randn(300) * 0.5

    assert train_x.shape == (300, 9)
    assert train_y.shape == (300,)

    gpr = PhysicsGPR()
    gpr.train(train_x, train_y, n_iter=100, verbose=False)
    assert gpr.is_trained

    pred = gpr.predict(train_x[0].tolist())
    assert pred.mean is not None
    assert pred.std > 0
    assert pred.conf_interval_95[0] < pred.conf_interval_95[1]

    means, stds = gpr.predict_batch(train_x[:10])
    assert means.shape == (10,)
    assert stds.shape == (10,)

    ood_x = torch.tensor([[50.0, 90.0, 30.0, 40.0, 5.0, 80.0, 30.0, 5.0, 0.5]])
    ood_pred = gpr.predict(ood_x[0].tolist())
    assert ood_pred.std > pred.std * 2

    print(f"GPR test passed: {len(ingredients)} ingredients, 300 samples")
    print(f"In-distribution: {pred.mean:.2f} +/- {pred.std:.2f}")
    print(f"Out-of-distribution: {ood_pred.mean:.2f} +/- {ood_pred.std:.2f}")

    assert abs(pred.mean - train_y[0].item()) < 5.0


if __name__ == "__main__":
    test_gpr_training()
