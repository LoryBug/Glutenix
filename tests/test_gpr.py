import pytest
import torch

from glutenix.db.models import Ingredient
from glutenix.db.seed import _seed_applications, _seed_ingredients
from glutenix.ml.gpr import PhysicsGPR
from glutenix.ml.train import generate_synthetic_data


@pytest.fixture
def seeded_session(db_session):
    _seed_ingredients(db_session)
    _seed_applications(db_session)
    db_session.commit()
    return db_session


def test_gpr_training(seeded_session):
    ingredients = seeded_session.query(Ingredient).all()

    train_x, train_y = generate_synthetic_data(ingredients, n_samples=80)
    train_y += torch.randn(80) * 0.5

    assert train_x.shape == (80, 9)
    assert train_y.shape == (80,)

    gpr = PhysicsGPR()
    gpr.train(train_x, train_y, n_iter=30, verbose=False)
    assert gpr.is_trained

    pred = gpr.predict(train_x[0].tolist())
    assert pred.mean is not None
    assert pred.std > 0
    assert pred.conf_interval_95[0] < pred.conf_interval_95[1]

    means, stds = gpr.predict_batch(train_x[:5])
    assert means.shape == (5,)
    assert stds.shape == (5,)

    ood_x = torch.tensor([[50.0, 90.0, 30.0, 40.0, 5.0, 80.0, 30.0, 5.0, 0.5]])
    ood_pred = gpr.predict(ood_x[0].tolist())
    assert ood_pred.std > pred.std * 2

    assert abs(pred.mean - train_y[0].item()) < 5.0


def test_gpr_save_load_roundtrip(seeded_session, tmp_path):
    ingredients = seeded_session.query(Ingredient).all()
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


def test_gpr_validation(seeded_session):
    ingredients = seeded_session.query(Ingredient).all()
    train_x, train_y = generate_synthetic_data(ingredients, n_samples=80)

    gpr = PhysicsGPR()
    gpr.train(train_x, train_y, n_iter=100, val_split=0.2, patience=10, verbose=False)

    assert gpr.is_trained
    assert len(gpr.train_history) > 0
    assert all(h.train_loss is not None and not (h.train_loss != h.train_loss) for h in gpr.train_history)  # no NaN
    assert any(h.val_loss is not None for h in gpr.train_history)
    assert all(h.iteration > 0 for h in gpr.train_history)


def test_gpr_evaluate(seeded_session):
    ingredients = seeded_session.query(Ingredient).all()
    train_x, train_y = generate_synthetic_data(ingredients, n_samples=100)

    gpr = PhysicsGPR()
    gpr.train(train_x[:80], train_y[:80], n_iter=30, verbose=False)

    metrics = gpr.evaluate(train_x[80:], train_y[80:])
    assert metrics.rmse >= 0
    assert metrics.mae >= 0
    assert metrics.r2 <= 1.0


def test_synthetic_baking_target(seeded_session):
    ingredients = seeded_session.query(Ingredient).all()

    train_x, train_y = generate_synthetic_data(ingredients, n_samples=30, target="baking")
    assert train_x.shape == (30, 9)
    assert train_y.shape == (30,)
    assert all(y > 0 for y in train_y.tolist())

    gpr = PhysicsGPR()
    gpr.train(train_x, train_y, n_iter=20, verbose=False)
    assert gpr.is_trained


if __name__ == "__main__":
    import tempfile
    from pathlib import Path
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from glutenix.db.base import Base

    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session = sessionmaker(engine)()
    _seed_ingredients(session)
    _seed_applications(session)
    session.commit()
    test_gpr_training(session)

    test_gpr_save_load_roundtrip(session, Path(tempfile.mkdtemp()))
    session.close()
