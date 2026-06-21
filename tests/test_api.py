from collections.abc import Generator
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from glutenix.api.deps import get_db
from glutenix.api.server import app
from glutenix.calibration.literature import DEFAULT_BREAD_DATASET, load_literature_records
from glutenix.db.base import Base
from glutenix.db.models import Application, SimulationCandidate, SimulationRun
from glutenix.db.seed import _seed_applications, _seed_ingredients

client = TestClient(app)


def _source_count(records):
    return len({
        record.source.get("doi") or record.source.get("pmcid") or record.source.get("url")
        for record in records
    })


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


def _test_session() -> Session:
    return next(app.dependency_overrides[get_db]())


def _create_test_candidate() -> SimulationCandidate:
    session = _test_session()
    pane = session.query(Application).filter(Application.name == "Pane").first()
    run = SimulationRun(
        application_id=pane.id,
        application_name="Pane",
        source="test",
        preset="test-preset",
        seed=123,
        blend_samples=10,
        process_samples=5,
        top_n=1,
        process_bounds=json.dumps({"baking_temp_c": {"min": 200, "max": 220}}),
        parameters=json.dumps({"test": True}),
        git_commit="testcommit",
        notes="test run",
    )
    session.add(run)
    session.flush()
    candidate = SimulationCandidate(
        run_id=run.id,
        rank=1,
        score=0.75,
        process_score=0.64,
        blend_score=0.82,
        flavor_score=0.91,
        proportions=json.dumps({
            "White rice flour": 0.5499,
            "Tapioca starch": 0.25,
            "Potato starch": 0.18,
            "Xanthan gum": 0.02,
        }),
        process=json.dumps({
            "fermentation_temp_c": 30,
            "fermentation_duration_min": 120,
            "baking_temp_c": 210,
            "baking_duration_min": 35,
        }),
        properties=json.dumps({
            "protein_pct": 4.2,
            "starch_pct": 80,
            "fat_pct": 0.9,
            "fiber_pct": 3.1,
            "water_absorption": 1.4,
            "viscosity_index": 1.8,
            "hydrocolloid_pct": 0.02,
            "amylose_pct": 20,
        }),
        metrics=json.dumps({
            "specific_volume_cm3_g": 2.2,
            "crumb_hardness_n": 12.0,
            "porosity_pct": 38.0,
        }),
        confidence=json.dumps({"score": 0.7, "level": "medium", "basis": [], "risk_flags": []}),
        risk_flags=json.dumps([]),
    )
    session.add(candidate)
    session.commit()
    session.refresh(candidate)
    return candidate


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
        assert len(data) == 32

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

    def test_create_unknown_ingredient_returns_404(self):
        resp = client.post("/blends", json={
            "name": "Bad ingredient blend",
            "ingredients": [
                {"ingredient_id": 999, "proportion": 1.0},
            ],
        })
        assert resp.status_code == 404

    def test_create_unknown_application_returns_404(self):
        resp = client.post("/blends", json={
            "name": "Bad app blend",
            "application_id": 999,
            "ingredients": [
                {"ingredient_id": 1, "proportion": 1.0},
            ],
        })
        assert resp.status_code == 404

    def test_duplicate_blend_name_returns_409(self):
        payload = {
            "name": "Duplicate blend",
            "ingredients": [
                {"ingredient_id": 1, "proportion": 1.0},
            ],
        }
        first = client.post("/blends", json=payload)
        assert first.status_code == 201
        second = client.post("/blends", json=payload)
        assert second.status_code == 409


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

    def test_simulate_rejects_negative_duration(self):
        resp = client.post("/simulate", json={
            "blend_id": 1,
            "fermentation_duration_min": -1,
        })
        assert resp.status_code == 422

    def test_simulate_cooking(self):
        resp = client.post("/blends", json={
            "name": "Cooking blend",
            "ingredients": [
                {"ingredient_id": 1, "proportion": 0.55},
                {"ingredient_id": 4, "proportion": 0.25},
                {"ingredient_id": 14, "proportion": 0.02},
                {"ingredient_id": 12, "proportion": 0.18},
            ],
        })
        blend_id = resp.json()["id"]

        resp = client.post("/simulate/cooking", json={
            "blend_id": blend_id,
            "water_temp_c": 98,
            "cooking_time_min": 6,
            "pasta_thickness_mm": 2,
            "water_to_flour_ratio": 6,
            "calcium_lactate_m": 0.1,
            "calcium_bath_time_min": 30,
            "dough_heat_temp_c": 80,
            "dough_heat_time_min": 60,
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "water_uptake_pct" in data
        assert data["cooking_loss_pct"] > 0
        assert data["swelling_index"] > 0
        assert 0 <= data["firmness_index"] <= 1
        assert 0 <= data["stickiness_index"] <= 1
        assert 0 <= data["quality_score"] <= 1
        assert data["gelation_index"] >= 0
        assert data["pregelatinization_index"] > 0
        assert data["syneresis_index"] >= 0
        assert data["starch_leaching_index"] >= 0
        assert data["process_family"] == "generic_fresh"
        assert data["calibration_confidence"] == "low"
        assert 0 <= data["calibration_score"] <= 1
        assert data["calibration_notes"]

    def test_simulate_cooking_not_found(self):
        resp = client.post("/simulate/cooking", json={"blend_id": 999})
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


class TestCalibration:
    def test_pasta_cooking_calibration(self):
        records = load_literature_records()
        resp = client.get("/calibration/pasta-cooking")
        assert resp.status_code == 200
        data = resp.json()
        assert data["n_records"] == len(records)
        assert data["source_count"] == _source_count(records)
        assert data["metric"] == "cooking_loss_pct"
        assert "before" in data
        assert "after" in data
        assert "metric_summaries" in data
        assert "grouped_errors" in data
        assert "source" in data["grouped_errors"]
        assert "process_family" in data["grouped_errors"]
        assert data["record_groups"]["process_family"]["fresh_calcium_gel"] == 30
        assert data["record_groups"]["process_family"]["dried_extruded"] == 10
        assert len(data["rows"]) == len(records)

    def test_bread_baking_calibration(self):
        records = load_literature_records(
            DEFAULT_BREAD_DATASET,
            required_measured_metrics=(),
            required_process_fields=("hydration_pct", "baking_time_min"),
        )
        resp = client.get("/calibration/bread-baking")
        assert resp.status_code == 200
        data = resp.json()
        assert data["n_records"] == len(records)
        assert data["source_count"] == _source_count(records)
        assert data["metric"] == "specific_volume_cm3_g"
        assert "specific_volume_cm3_g" in data["metric_summaries"]
        assert "porosity_pct" in data["metric_summaries"]
        assert data["record_groups"]["process_family"]["millet_cultivar_bread"] == 9
        assert data["record_groups"]["process_family"]["hydrocolloid_bread"] == 17
        assert data["record_groups"]["process_family"]["enzyme_hydrocolloid_bread"] == 12
        assert data["record_groups"]["process_family"]["protein_enriched_bread"] == 16
        assert len(data["rows"]) == len(records)

    def test_literature_coverage(self):
        pasta_records = load_literature_records()
        bread_records = load_literature_records(
            DEFAULT_BREAD_DATASET,
            required_measured_metrics=(),
            required_process_fields=("hydration_pct", "baking_time_min"),
        )
        resp = client.get("/calibration/coverage")
        assert resp.status_code == 200
        data = resp.json()
        assert set(data["domains"]) == {"pasta_cooking", "bread_baking"}
        assert data["domains"]["pasta_cooking"]["record_count"] == len(pasta_records)
        assert data["domains"]["bread_baking"]["record_count"] == len(bread_records)
        assert "hydration_pct" in data["domains"]["bread_baking"]["process_ranges"]
        assert "water_to_flour_ratio" in data["domains"]["pasta_cooking"]["process_ranges"]


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

    def test_suggest_respects_bounds_after_normalization(self):
        resp = client.post("/optimize/suggest", json={
            "ingredients": [
                {"ingredient_id": 1, "min_proportion": 0.7, "max_proportion": 0.8},
                {"ingredient_id": 11, "min_proportion": 0.2, "max_proportion": 0.3},
            ],
            "n_candidates": 3,
            "n_samples": 100,
        })
        assert resp.status_code == 200, resp.text
        for candidate in resp.json()["candidates"]:
            rice = candidate["proportions"]["White rice flour"]
            starch = candidate["proportions"]["Potato starch"]
            assert 0.7 <= rice <= 0.8
            assert 0.2 <= starch <= 0.3
            assert abs(sum(candidate["proportions"].values()) - 1.0) <= 0.001

    def test_application_suggest(self):
        resp = client.post("/optimize/application-suggest", json={
            "application_id": 1,
            "ingredients": [
                {"ingredient_id": 1, "min_proportion": 0.35, "max_proportion": 0.8},
                {"ingredient_id": 11, "min_proportion": 0.10, "max_proportion": 0.45},
                {"ingredient_id": 14, "min_proportion": 0.01, "max_proportion": 0.05},
            ],
            "n_candidates": 2,
            "n_blend_samples": 10,
            "n_process_samples": 5,
            "seed": 123,
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["application"] == "Pizza"
        assert data["target_profile"] == "Pizza"
        assert data["flavor_target"] == "Pizza"
        assert len(data["candidates"]) == 2
        candidate = data["candidates"][0]
        assert candidate["score"] >= 0
        assert candidate["process_score"] >= 0
        assert candidate["blend_score"] >= 0
        assert candidate["flavor_score"] >= 0
        assert len(candidate["proportions"]) == 3
        assert "fermentation_temp_c" in candidate["process"]
        assert "water_absorption" in candidate["properties"]
        assert "neutral" in candidate["flavor_profile"]
        assert 0 <= candidate["model_confidence"]["score"] <= 1
        assert candidate["model_confidence"]["level"] in {"low", "medium", "high"}
        assert candidate["model_confidence"]["basis"]
        assert candidate["model_confidence"]["risk_flags"]
        assert any("Literature coverage/OOD" in item for item in candidate["model_confidence"]["basis"])

    def test_flavor_targets(self):
        resp = client.get("/optimize/flavor-targets")
        assert resp.status_code == 200
        data = resp.json()
        names = {target["name"] for target in data}
        assert {"Generico", "Pizza", "Pane"}.issubset(names)
        pizza = next(target for target in data if target["name"] == "Pizza")
        assert pizza["evidence_level"] == "heuristic"
        assert "neutral" in pizza["profile"]

    def test_application_suggest_not_found(self):
        resp = client.post("/optimize/application-suggest", json={
            "application_id": 999,
            "ingredients": [{"ingredient_id": 1}, {"ingredient_id": 2}],
        })
        assert resp.status_code == 404

    def test_application_suggest_impossible_bounds(self):
        resp = client.post("/optimize/application-suggest", json={
            "application_id": 1,
            "ingredients": [
                {"ingredient_id": 1, "min_proportion": 0.8, "max_proportion": 1.0},
                {"ingredient_id": 2, "min_proportion": 0.8, "max_proportion": 1.0},
            ],
            "n_blend_samples": 10,
            "n_process_samples": 5,
        })
        assert resp.status_code == 200
        assert resp.json()["candidates"] == []

    def test_application_suggest_pasta_uses_cooking(self):
        resp = client.post("/optimize/application-suggest", json={
            "application_id": 5,
            "ingredients": [
                {"ingredient_id": 1, "min_proportion": 0.30, "max_proportion": 0.70},
                {"ingredient_id": 4, "min_proportion": 0.10, "max_proportion": 0.50},
                {"ingredient_id": 14, "min_proportion": 0.005, "max_proportion": 0.025},
            ],
            "n_candidates": 2,
            "n_blend_samples": 10,
            "n_process_samples": 5,
            "seed": 99,
            "baking_temp": {"min": 92, "max": 100},
            "baking_duration": {"min": 4, "max": 12},
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["application"] == "Pasta fresca"
        assert len(data["candidates"]) == 2
        candidate = data["candidates"][0]
        assert "water_temp_c" in candidate["process"]
        assert candidate["cooking_metrics"] is not None
        assert candidate["cooking_metrics"]["cooking_loss_pct"] > 0
        assert "calibration_confidence" in candidate["cooking_metrics"]
        assert 0 <= candidate["model_confidence"]["score"] <= 1
        assert candidate["model_confidence"]["level"] in {"low", "medium", "high"}

    def test_application_suggest_pane_uses_bread_quality(self):
        resp = client.post("/optimize/application-suggest", json={
            "application_id": 2,
            "ingredients": [
                {"ingredient_id": 1, "min_proportion": 0.45, "max_proportion": 0.75},
                {"ingredient_id": 12, "min_proportion": 0.20, "max_proportion": 0.50},
                {"ingredient_id": 17, "min_proportion": 0.01, "max_proportion": 0.03},
            ],
            "n_candidates": 3,
            "n_blend_samples": 12,
            "n_process_samples": 5,
            "seed": 101,
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["application"] == "Pane"
        assert len(data["candidates"]) == 3
        for candidate in data["candidates"]:
            assert candidate["cooking_metrics"] is None
            assert candidate["bread_metrics"] is not None
            assert candidate["bread_metrics"]["specific_volume_cm3_g"] > 0
            assert "calibration_score" in candidate["bread_metrics"]
            assert any("Bread quality model" in note for note in candidate["model_confidence"]["basis"])
            assert not any("No direct experimental calibration" in flag for flag in candidate["model_confidence"]["risk_flags"])


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

    def test_create_unknown_blend_returns_404(self):
        resp = client.post("/experiments", json={
            "blend_id": 999,
            "conditions": "{}",
            "metrics": "{}",
        })
        assert resp.status_code == 404

    def test_create_rejects_invalid_json(self):
        resp = client.post("/experiments", json={
            "blend_id": 1,
            "conditions": "not-json",
            "metrics": "{}",
        })
        assert resp.status_code == 422


class TestInternalWorkflow:
    def test_simulation_run_list_show_and_candidate_patch(self):
        candidate = _create_test_candidate()

        resp = client.get("/simulation-runs")
        assert resp.status_code == 200
        assert resp.json()[0]["id"] == candidate.run_id
        assert resp.json()[0]["candidate_count"] == 1

        resp = client.get(f"/simulation-runs/{candidate.run_id}")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["parameters"] == {"test": True}
        assert payload["candidates"][0]["proportions"]["White rice flour"] == 0.5499

        resp = client.patch(
            f"/simulation-candidates/{candidate.id}",
            json={"status": "test_next", "notes": "ready for physical test"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "test_next"
        assert resp.json()["decision_notes"] == "ready for physical test"

    def test_candidate_cohort_analysis_filters_saved_candidates(self):
        candidate = _create_test_candidate()
        client.patch(f"/simulation-candidates/{candidate.id}", json={"status": "test_next"})
        other = _create_test_candidate()
        client.patch(f"/simulation-candidates/{other.id}", json={"status": "avoid"})

        resp = client.get("/simulation-candidates/cohort", params={
            "application": "Pane",
            "status": "test_next",
            "max_rank": 1,
        })

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["candidate_count"] == 1
        assert payload["status_counts"] == {"test_next": 1}
        assert payload["ingredients"]["White rice flour"]["mean"] == 54.99
        assert payload["metrics"]["specific_volume_cm3_g"]["mean"] == 2.2
        assert payload["top_candidates"][0]["candidate_id"] == candidate.id

    def test_promote_candidate_to_blend(self):
        candidate = _create_test_candidate()

        resp = client.post(
            f"/simulation-candidates/{candidate.id}/promote-blend",
            json={"name": "API promoted blend"},
        )

        assert resp.status_code == 200, resp.text
        payload = resp.json()
        assert payload["candidate_id"] == candidate.id
        assert payload["created"] is True

        resp = client.get(f"/blends/{payload['blend_id']}")
        assert resp.status_code == 200
        assert len(resp.json()["ingredients"]) == 4

    def test_create_experiment_from_candidate(self):
        candidate = _create_test_candidate()

        resp = client.post("/experiments/from-candidate", json={
            "candidate_id": candidate.id,
            "conditions": {"dry_blend_g": 500, "water_added_g": 700},
            "metrics": {"specific_volume_cm3_g": 2.35, "flavor_score": 4},
        })

        assert resp.status_code == 201, resp.text
        payload = resp.json()
        assert payload["candidate_id"] == candidate.id
        assert payload["conditions"]["simulation_run_id"] == candidate.run_id
        assert payload["metrics"]["specific_volume_cm3_g"] == 2.35

    def test_candidate_feedback_handles_no_experiments(self):
        candidate = _create_test_candidate()

        resp = client.get(f"/simulation-candidates/{candidate.id}/feedback")

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["experiment_count"] == 0
        assert payload["comparisons"] == []
        assert payload["summary"]["status"] == "no_experiments"

    def test_candidate_feedback_compares_measured_metrics(self):
        candidate = _create_test_candidate()
        client.post("/experiments/from-candidate", json={
            "candidate_id": candidate.id,
            "conditions": {"dry_blend_g": 500},
            "metrics": {
                "specific_volume_cm3_g": 2.42,
                "crumb_hardness_n": 11.5,
                "flavor_score": 0.86,
                "operator_notes": "good handling",
            },
        })

        resp = client.get(f"/simulation-candidates/{candidate.id}/experiments")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["conditions"]["candidate_id"] == candidate.id

        resp = client.get(f"/simulation-candidates/{candidate.id}/feedback")

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["experiment_count"] == 1
        compared_metrics = {item["metric"] for item in payload["comparisons"]}
        assert {"specific_volume_cm3_g", "crumb_hardness_n", "flavor_score"}.issubset(compared_metrics)
        assert "operator_notes" not in compared_metrics
        volume = next(item for item in payload["comparisons"] if item["metric"] == "specific_volume_cm3_g")
        assert volume["predicted"] == 2.2
        assert volume["measured"] == 2.42
        assert volume["absolute_delta"] == 0.22
        assert payload["summary"]["status"] == "compared"

    def test_candidate_feedback_skips_sparse_unmatched_metrics(self):
        candidate = _create_test_candidate()
        client.post("/experiments/from-candidate", json={
            "candidate_id": candidate.id,
            "conditions": {},
            "metrics": {"unmatched_metric": 123, "notes": "not comparable"},
        })

        resp = client.get(f"/simulation-candidates/{candidate.id}/feedback")

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["experiment_count"] == 1
        assert payload["comparisons"] == []
        assert payload["summary"]["status"] == "no_comparable_metrics"

    def test_compare_blends_accepts_candidates_blends_and_custom_formula(self):
        candidate = _create_test_candidate()
        promoted = client.post(f"/simulation-candidates/{candidate.id}/promote-blend", json={}).json()

        resp = client.post("/compare/blends", json={
            "application": "Pane",
            "items": [
                {"candidate_id": candidate.id},
                {"blend_id": promoted["blend_id"]},
                {
                    "name": "custom formula",
                    "proportions": {
                        "White rice flour": 0.5,
                        "Tapioca starch": 0.28,
                        "Potato starch": 0.2,
                        "Xanthan gum": 0.02,
                    },
                },
            ],
            "n_process_samples": 5,
            "seed": 77,
        })

        assert resp.status_code == 200, resp.text
        payload = resp.json()
        assert payload["application"] == "Pane"
        assert len(payload["ranking"]) == 3
        assert payload["ranking"][0]["rank"] == 1
        assert payload["ranking"][0]["bread_metrics"]["specific_volume_cm3_g"] > 0
        assert "flavor_score" in payload["ranking"][0]
