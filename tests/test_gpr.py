import pytest
import torch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from glutenix.db.base import Base
from glutenix.db.models import Ingredient
from glutenix.db.seed import _seed_ingredients, _seed_applications
from glutenix.ml.gpr import PhysicsGPR
from glutenix.ml.train import generate_synthetic_data


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session = sessionmaker(engine)()
    _seed_ingredients(session)
    _seed_applications(session)
    session.commit()
    yield session
    session.close()


def test_gpr_training(db_session):
    ingredients = db_session.query(Ingredient).all()

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

    assert abs(pred.mean - train_y[0].item()) < 5.0


def test_gpr_save_load_roundtrip(db_session, tmp_path):
    ingredients = db_session.query(Ingredient).all()
    train_x, train_y = generate_synthetic_data(ingredients, n_samples=50)

    gpr = PhysicsGPR()
    gpr.train(train_x, train_y, n_iter=20, verbose=False)

    before_mean, before_std = gpr.predict_batch(train_x[:5])

    path = tmp_path / "gpr.pt"
    gpr.save(str(path))
    loaded = PhysicsGPR.load(str(path))

    after_mean, after_std = loaded.predict_batch(train_x[:5])

    torch.testing.assert_close(after_mean, before_mean)
    torch.testing.assert_close(after_std, before_std)


if __name__ == "__main__":
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session = sessionmaker(engine)()
    _seed_ingredients(session)
    _seed_applications(session)
    session.commit()
    test_gpr_training(session)
    session.close()
