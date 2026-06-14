from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from glutenix.api.deps import get_db
from glutenix.api.server import app
from glutenix.db.base import Base
from glutenix.db.seed import _seed_applications, _seed_ingredients

client = TestClient(app)


@pytest.fixture(autouse=True)
def _setup_db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    conn = engine.connect()
    session = Session(bind=conn)

    _seed_ingredients(session)
    _seed_applications(session)
    session.commit()

    def _get_test_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = _get_test_db
    yield
    session.close()
    conn.close()
    app.dependency_overrides.clear()


class TestHealth:
    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestIngredients:
    def test_list(self):
        resp = client.get("/ingredients")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 17

    def test_get_found(self):
        resp = client.get("/ingredients/1")
        assert resp.status_code == 200
        assert resp.json()["id"] == 1

    def test_get_not_found(self):
        resp = client.get("/ingredients/999")
        assert resp.status_code == 404

    def test_create(self):
        resp = client.post("/ingredients", json={
            "name": "Test flour", "category": "flour", "protein_pct": 12.0,
        })
        assert resp.status_code == 201
        assert resp.json()["name"] == "Test flour"


class TestApplications:
    def test_list(self):
        resp = client.get("/applications")
        assert resp.status_code == 200
        assert len(resp.json()) == 5

    def test_get_found(self):
        resp = client.get("/applications/1")
        assert resp.status_code == 200

    def test_get_not_found(self):
        resp = client.get("/applications/999")
        assert resp.status_code == 404


class TestBlends:
    def test_create_and_list(self):
        resp = client.post("/blends", json={
            "name": "Test blend",
            "ingredients": [
                {"ingredient_id": 1, "proportion": 0.7},
                {"ingredient_id": 2, "proportion": 0.3},
            ],
        })
        assert resp.status_code == 201
        blend_id = resp.json()["id"]

        resp = client.get("/blends")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        resp = client.get(f"/blends/{blend_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test blend"


class TestSimulation:
    def test_simulate(self):
        resp = client.post("/blends", json={
            "name": "Sim blend",
            "ingredients": [
                {"ingredient_id": 1, "proportion": 0.7},
                {"ingredient_id": 2, "proportion": 0.3},
            ],
        })
        blend_id = resp.json()["id"]

        resp = client.post("/simulate", json={"blend_id": blend_id})
        assert resp.status_code == 200
        data = resp.json()
        assert data["viscosity_index"] > 0
        assert data["fermentation_volume_increase"] > 0
        assert data["baking_core_temp_c"] > 0

    def test_simulate_not_found(self):
        resp = client.post("/simulate", json={"blend_id": 999})
        assert resp.status_code == 404


class TestPrediction:
    def test_untrained(self):
        resp = client.post("/predict", json={
            "features": [5.0, 70.0, 2.0, 3.0, 1.5, 65.0, 20.0, 1.2, 0.02],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["mean"] == 0.0


class TestARD:
    def test_ard_untrained(self):
        resp = client.get("/optimize/ard")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["importance"]) == 9


class TestUpdateIngredient:
    def test_update(self):
        resp = client.put("/ingredients/1", json={
            "name": "White rice flour UPDATED", "category": "flour", "protein_pct": 8.0,
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "White rice flour UPDATED"

    def test_update_not_found(self):
        resp = client.put("/ingredients/999", json={
            "name": "None", "category": "flour",
        })
        assert resp.status_code == 404


class TestOptimizeSuggest:
    def test_suggest(self):
        resp = client.post("/optimize/suggest", json={
            "ingredients": [{"ingredient_id": 1}, {"ingredient_id": 11}],
            "n_candidates": 3,
            "n_samples": 100,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["candidates"]) == 3
        for c in data["candidates"]:
            assert "volume_increase_pct" in c
            assert "core_temp_c" in c
            assert len(c["proportions"]) == 2


class TestExperiments:
    def test_crud(self):
        resp = client.post("/blends", json={
            "name": "Exp blend",
            "ingredients": [
                {"ingredient_id": 1, "proportion": 0.7},
                {"ingredient_id": 2, "proportion": 0.3},
            ],
        })
        blend_id = resp.json()["id"]

        resp = client.post("/experiments", json={
            "blend_id": blend_id,
            "conditions": '{"temp": 25, "humidity": 60}',
            "metrics": '{"volume": 180, "core_temp": 95}',
        })
        assert resp.status_code == 201
        exp_id = resp.json()["id"]

        resp = client.get("/experiments")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

        resp = client.get(f"/experiments/{exp_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == exp_id

        resp = client.delete(f"/experiments/{exp_id}")
        assert resp.status_code == 204

        resp = client.get(f"/experiments/{exp_id}")
        assert resp.status_code == 404
