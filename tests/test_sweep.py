from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from glutenix.api.deps import get_db
from glutenix.api.server import app
from glutenix.db.base import Base
from glutenix.db.seed import _seed_applications, _seed_ingredients
from glutenix.engine.blend import BlendProperties
from glutenix.engine.sweep import SimulationSweeper, SweepRange

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


class TestSweeper:
    def test_generate_grid_defaults(self):
        sweeper = SimulationSweeper()
        ft = SweepRange(min=25, max=30, step=5)
        fd = SweepRange(min=60, max=120, step=60)
        bt = SweepRange(min=180, max=200, step=20)
        bd = SweepRange(min=15, max=25, step=10)
        points = sweeper.generate_grid(ft, fd, bt, bd)
        expected = 2 * 2 * 2 * 2
        assert len(points) == expected
        assert all("fermentation_temp_c" in p for p in points)

    def test_generate_random(self):
        sweeper = SimulationSweeper()
        ft = SweepRange(min=25, max=35)
        fd = SweepRange(min=60, max=180)
        bt = SweepRange(min=180, max=220)
        bd = SweepRange(min=15, max=35)
        points = sweeper.generate_random(ft, fd, bt, bd, n_samples=50, seed=42)
        assert len(points) == 50
        assert all(25 <= p["fermentation_temp_c"] <= 35 for p in points)

    def test_composite_score_volume_only(self):
        score = SimulationSweeper._compute_composite_score(
            volume_increase=0.70,
            core_temp_c=90,
            crust_temp_c=180,
            w_volume=1.0,
            w_gelatinization=0.0,
            w_crust=0.0,
            w_efficiency=0.0,
        )
        assert score == pytest.approx(1.0, abs=1e-4)

    def test_composite_score_penalizes_volume_far_from_target(self):
        target = SimulationSweeper._compute_composite_score(
            volume_increase=0.70,
            core_temp_c=90,
            crust_temp_c=170,
            w_volume=1.0,
            w_gelatinization=0.0,
            w_crust=0.0,
            w_efficiency=0.0,
        )
        low = SimulationSweeper._compute_composite_score(
            volume_increase=0.05,
            core_temp_c=90,
            crust_temp_c=170,
            w_volume=1.0,
            w_gelatinization=0.0,
            w_crust=0.0,
            w_efficiency=0.0,
        )
        assert target > low

    def test_composite_score_gelatinization(self):
        props = BlendProperties(
            gelatinization_temp_min=62, gelatinization_temp_max=78
        )
        score = SimulationSweeper._compute_composite_score(
            volume_increase=0.5,
            core_temp_c=90,
            crust_temp_c=180,
            blend_props=props,
            w_volume=0.0,
            w_gelatinization=1.0,
            w_crust=0.0,
            w_efficiency=0.0,
        )
        assert score == pytest.approx(1.0, abs=1e-4)

    def test_composite_score_efficiency(self):
        short = SimulationSweeper._compute_composite_score(
            volume_increase=0.5,
            core_temp_c=90,
            crust_temp_c=170,
            fermentation_duration_min=80,
            baking_duration_min=30,
            w_volume=0.0,
            w_gelatinization=0.0,
            w_crust=0.0,
            w_efficiency=1.0,
        )
        long = SimulationSweeper._compute_composite_score(
            volume_increase=0.5,
            core_temp_c=90,
            crust_temp_c=170,
            fermentation_duration_min=260,
            baking_duration_min=40,
            w_volume=0.0,
            w_gelatinization=0.0,
            w_crust=0.0,
            w_efficiency=1.0,
        )
        assert short > long

    def test_run_sweep_returns_sorted(self):
        sweeper = SimulationSweeper()
        props = BlendProperties(
            viscosity_index=1.5,
            gelatinization_temp_min=62,
            gelatinization_temp_max=78,
        )
        param_points = [
            {"fermentation_temp_c": 30, "fermentation_duration_min": 120,
             "baking_temp_c": 200, "baking_duration_min": 25},
            {"fermentation_temp_c": 35, "fermentation_duration_min": 60,
             "baking_temp_c": 190, "baking_duration_min": 20},
            {"fermentation_temp_c": 25, "fermentation_duration_min": 90,
             "baking_temp_c": 210, "baking_duration_min": 30},
        ]
        result = sweeper.run_sweep(props, param_points, top_n=3)
        assert len(result.points) == 3
        assert result.n_total == 3
        scores = [p.composite_score for p in result.points]
        assert scores == sorted(scores, reverse=True)

    def test_run_sweep_empty_params(self):
        sweeper = SimulationSweeper()
        props = BlendProperties()
        result = sweeper.run_sweep(props, [], top_n=5)
        assert len(result.points) == 0
        assert result.n_total == 0


class TestSweepAPI:
    def test_sweep_endpoint(self):
        resp = client.post("/blends", json={
            "name": "Sweep blend",
            "ingredients": [
                {"ingredient_id": 1, "proportion": 0.7},
                {"ingredient_id": 2, "proportion": 0.3},
            ],
        })
        blend_id = resp.json()["id"]

        response = client.post("/simulate/sweep", json={
            "blend_id": blend_id,
            "strategy": "grid",
            "fermentation_temp": {"min": 28, "max": 32, "step": 4},
            "fermentation_duration": {"min": 90, "max": 150, "step": 60},
            "baking_temp": {"min": 190, "max": 210, "step": 20},
            "baking_duration": {"min": 20, "max": 30, "step": 10},
            "top_n": 5,
        })
        assert response.status_code == 200, response.text
        data = response.json()
        assert "points" in data
        assert "n_total" in data
        assert data["n_total"] == 16
        assert len(data["points"]) <= 5
        assert data["target_profile"] == "Generico"
        assert data["target_profile_details"]["evidence_level"] == "heuristic"
        assert data["target_profile_details"]["sources"]
        if data["points"]:
            p = data["points"][0]
            assert "composite_score" in p
            assert "volume_increase" in p

    def test_sweep_random(self):
        resp = client.post("/blends", json={
            "name": "Sweep random",
            "ingredients": [
                {"ingredient_id": 1, "proportion": 1.0},
            ],
        })
        blend_id = resp.json()["id"]

        response = client.post("/simulate/sweep", json={
            "blend_id": blend_id,
            "strategy": "random",
            "n_samples": 30,
            "seed": 42,
            "top_n": 5,
        })
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["n_total"] == 30
        assert len(data["points"]) <= 5

    def test_sweep_blend_not_found(self):
        response = client.post("/simulate/sweep", json={
            "blend_id": 99999,
            "strategy": "random",
        })
        assert response.status_code == 404

    def test_sweep_invalid_strategy(self):
        resp = client.post("/blends", json={
            "name": "Sweep invalid",
            "ingredients": [
                {"ingredient_id": 1, "proportion": 1.0},
            ],
        })
        blend_id = resp.json()["id"]

        response = client.post("/simulate/sweep", json={
            "blend_id": blend_id,
            "strategy": "unknown",
        })
        assert response.status_code == 422

    def test_sweep_rejects_inverted_range(self):
        resp = client.post("/blends", json={
            "name": "Sweep inverted range",
            "ingredients": [
                {"ingredient_id": 1, "proportion": 1.0},
            ],
        })
        blend_id = resp.json()["id"]

        response = client.post("/simulate/sweep", json={
            "blend_id": blend_id,
            "fermentation_temp": {"min": 35, "max": 25, "step": 1},
        })
        assert response.status_code == 422

    def test_sweep_rejects_non_positive_step(self):
        resp = client.post("/blends", json={
            "name": "Sweep bad step",
            "ingredients": [
                {"ingredient_id": 1, "proportion": 1.0},
            ],
        })
        blend_id = resp.json()["id"]

        response = client.post("/simulate/sweep", json={
            "blend_id": blend_id,
            "baking_duration": {"min": 20, "max": 30, "step": 0},
        })
        assert response.status_code == 422

    def test_sweep_uses_application_profile(self):
        resp = client.post("/blends", json={
            "name": "Sweep pizza profile",
            "ingredients": [
                {"ingredient_id": 1, "proportion": 1.0},
            ],
        })
        blend_id = resp.json()["id"]

        response = client.post("/simulate/sweep", json={
            "blend_id": blend_id,
            "application_id": 1,
            "strategy": "random",
            "n_samples": 20,
            "top_n": 3,
            "seed": 7,
        })
        assert response.status_code == 200, response.text
        assert response.json()["target_profile"] == "Pizza"
        assert "pizza" in response.json()["target_profile_details"]["rationale"].lower()

    def test_list_target_profiles(self):
        response = client.get("/simulate/target-profiles")
        assert response.status_code == 200, response.text
        data = response.json()
        names = {profile["name"] for profile in data}
        assert {"Generico", "Pizza", "Pane", "Frolla"}.issubset(names)
        pizza = next(profile for profile in data if profile["name"] == "Pizza")
        assert pizza["evidence_level"] == "heuristic"
        assert pizza["sources"]
        assert pizza["volume_target"] > 0

    def test_sweep_application_not_found(self):
        resp = client.post("/blends", json={
            "name": "Sweep unknown profile",
            "ingredients": [
                {"ingredient_id": 1, "proportion": 1.0},
            ],
        })
        blend_id = resp.json()["id"]

        response = client.post("/simulate/sweep", json={
            "blend_id": blend_id,
            "application_id": 99999,
            "strategy": "random",
        })
        assert response.status_code == 404
