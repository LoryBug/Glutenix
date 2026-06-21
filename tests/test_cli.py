import json

import pytest

import glutenix.cli as cli_mod
from glutenix.analysis.coverage_gaps import coverage_gaps_report
from glutenix.cli import (
    APPLICATION_PRESETS,
    APPLICATION_PRESET_METADATA,
    APPLICATION_PRESET_PROCESS_BOUNDS,
    PRESETS,
    list_saved_runs,
    main,
    mark_candidate,
    rank_application_candidates,
    rank_pane_candidates,
    save_application_run,
    save_pane_run,
)
from glutenix.db.models import Blend, ExperimentResult
from glutenix.db.seed import _seed_applications, _seed_ingredients


def test_rank_pane_candidates_returns_sorted_candidates():
    candidates = rank_pane_candidates(
        preset="sorghum-baseline",
        n_blend_samples=5,
        n_process_samples=3,
        top=3,
        seed=42,
    )

    assert len(candidates) == 3
    assert [candidate.rank for candidate in candidates] == [1, 2, 3]
    assert candidates[0].score >= candidates[-1].score
    assert abs(sum(candidates[0].proportions.values()) - 1.0) <= 0.001
    assert candidates[0].bread_metrics["specific_volume_cm3_g"] > 0
    assert candidates[0].model_confidence["level"] in {"low", "medium", "high"}
    assert candidates[0].model_confidence["confidence_summary"] in {
        "calibrated",
        "literature_informed",
        "heuristic",
        "ood_extrapolation",
    }
    assert "risk_warnings" in candidates[0].model_confidence


def test_cli_rank_pane_writes_json(tmp_path):
    output_path = tmp_path / "pane-ranking.json"

    exit_code = main([
        "rank-pane",
        "--preset",
        "freee-inspired",
        "--blend-samples",
        "4",
        "--process-samples",
        "3",
        "--top",
        "2",
        "--seed",
        "7",
        "--json",
        str(output_path),
    ])

    assert exit_code == 0
    rows = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(rows) == 2
    assert rows[0]["rank"] == 1
    assert "proportions" in rows[0]
    assert "bread_metrics" in rows[0]


def test_rank_application_candidates_returns_application_suggestion(db_session):
    _seed_ingredients(db_session)
    _seed_applications(db_session)
    db_session.commit()

    result = rank_application_candidates(
        application="Pane",
        bounds=PRESETS["bobs-inspired"],
        n_blend_samples=10,
        n_process_samples=5,
        top=3,
        seed=42,
        db=db_session,
    )

    assert result.application == "Pane"
    assert len(result.candidates) == 3
    assert [candidate.rank for candidate in result.candidates] == [1, 2, 3]
    assert result.candidates[0].score >= result.candidates[-1].score
    assert result.candidates[0].flavor_score > 0
    assert result.candidates[0].bread_metrics is not None
    assert result.candidates[0].bread_metrics["specific_volume_cm3_g"] > 0


def test_rank_application_candidates_supports_pasta_v1(db_session):
    _seed_ingredients(db_session)
    _seed_applications(db_session)
    db_session.commit()

    result = rank_application_candidates(
        application="Pasta fresca",
        bounds=APPLICATION_PRESETS["pasta-rice-structure-v1"],
        n_blend_samples=10,
        n_process_samples=5,
        top=3,
        seed=43,
        db=db_session,
    )

    assert result.application == "Pasta fresca"
    assert len(result.candidates) == 3
    assert result.candidates[0].cooking_metrics is not None
    assert result.candidates[0].bread_metrics is None
    assert result.candidates[0].cooking_metrics["cooking_loss_pct"] > 0
    assert "firmness_index" in result.candidates[0].cooking_metrics
    assert result.candidates[0].cooking_metrics["process_family"] == "fresh_calcium_gel"
    assert result.candidates[0].process["water_temp_c"] == 100.0
    assert result.candidates[0].process["water_to_flour_ratio"] == 3.0
    assert result.candidates[0].process["calcium_lactate_m"] == 0.1
    assert result.candidates[0].process["calcium_bath_time_min"] == 30.0
    assert result.candidates[0].model_confidence.level in {"low", "medium", "high"}
    assert result.candidates[0].model_confidence.confidence_summary in {
        "calibrated",
        "literature_informed",
        "heuristic",
        "ood_extrapolation",
    }


def test_rank_application_candidates_supports_pizza_v1(db_session):
    _seed_ingredients(db_session)
    _seed_applications(db_session)
    db_session.commit()

    result = rank_application_candidates(
        application="Pizza",
        bounds=APPLICATION_PRESETS["pizza-v1"],
        n_blend_samples=10,
        n_process_samples=5,
        top=2,
        seed=44,
        process_bounds=APPLICATION_PRESET_PROCESS_BOUNDS["pizza-v1"],
        db=db_session,
    )

    assert result.application == "Pizza"
    assert result.preset_metadata is not None
    assert result.preset_metadata["audit_doc"] == "docs/pizza-v1-literature-audit.md"
    assert len(result.candidates) == 2
    assert result.candidates[0].coverage_diagnostics is not None
    assert result.candidates[0].coverage_diagnostics["preset"] == "pizza-v1"
    assert 0 <= result.candidates[0].coverage_diagnostics["coverage_fraction"] <= 1


def test_pizza_v1_coverage_gaps_for_saved_candidate(db_session):
    _seed_ingredients(db_session)
    _seed_applications(db_session)
    db_session.commit()

    result = rank_application_candidates(
        application="Pizza",
        bounds=APPLICATION_PRESETS["pizza-v1"],
        n_blend_samples=10,
        n_process_samples=5,
        top=1,
        seed=45,
        process_bounds=APPLICATION_PRESET_PROCESS_BOUNDS["pizza-v1"],
        db=db_session,
    )
    run = save_application_run(
        db=db_session,
        result=result,
        preset="pizza-v1",
        seed=45,
        n_blend_samples=10,
        n_process_samples=5,
        top=1,
        process_bounds=APPLICATION_PRESET_PROCESS_BOUNDS["pizza-v1"],
        git_commit="testcommit",
    )

    report = coverage_gaps_report(db_session, application="Pizza", candidate_id=run.candidates[0].id)

    assert report["domain"] == "pizza_v1_audit"
    assert report["coverage_diagnostics"]["preset"] == "pizza-v1"
    assert report["candidate"]["assessment"]["calibration_coverage"] == 0.0


def test_cli_rank_application_writes_json(tmp_path):
    output_path = tmp_path / "application-ranking.json"

    exit_code = main([
        "rank-application",
        "--application",
        "Pane",
        "--preset",
        "bobs-inspired",
        "--blend-samples",
        "10",
        "--process-samples",
        "5",
        "--top",
        "2",
        "--seed",
        "7",
        "--json",
        str(output_path),
    ])

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["application"] == "Pane"
    assert len(payload["candidates"]) == 2
    assert "flavor_score" in payload["candidates"][0]
    assert "model_confidence" in payload["candidates"][0]


def test_cli_rank_application_writes_pasta_json(tmp_path):
    output_path = tmp_path / "pasta-ranking.json"

    exit_code = main([
        "rank-application",
        "--application",
        "Pasta fresca",
        "--preset",
        "pasta-rice-structure-v1",
        "--blend-samples",
        "10",
        "--process-samples",
        "5",
        "--top",
        "2",
        "--seed",
        "8",
        "--json",
        str(output_path),
    ])

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["application"] == "Pasta fresca"
    assert len(payload["candidates"]) == 2
    assert payload["candidates"][0]["cooking_metrics"]["cooking_loss_pct"] > 0
    assert payload["candidates"][0]["cooking_metrics"]["process_family"] == "fresh_calcium_gel"
    assert payload["candidates"][0]["process"]["calcium_lactate_m"] == 0.1
    assert payload["candidates"][0]["bread_metrics"] is None


def test_cli_pizza_v1_preset_requires_pizza_application():
    exit_code = main([
        "rank-application",
        "--application",
        "Pane",
        "--preset",
        "pizza-v1",
        "--blend-samples",
        "10",
        "--process-samples",
        "5",
        "--top",
        "1",
    ])

    assert exit_code == 2


def test_pane_presets_reference_seeded_ingredient_names():
    assert {"sorghum-baseline", "bobs-inspired", "schaer-inspired"}.issubset(PRESETS)
    assert "pasta-rice-structure-v1" in APPLICATION_PRESETS
    assert "pizza-v1" in APPLICATION_PRESETS
    assert APPLICATION_PRESET_METADATA["pizza-v1"]["audit_doc"] == "docs/pizza-v1-literature-audit.md"
    assert "pasta-rice-structure-v1" not in PRESETS


def test_save_list_and_mark_pane_run(db_session):
    _seed_ingredients(db_session)
    _seed_applications(db_session)
    db_session.commit()

    candidates = rank_pane_candidates(
        preset="bobs-inspired",
        n_blend_samples=4,
        n_process_samples=3,
        top=2,
        seed=11,
        db=db_session,
    )

    run = save_pane_run(
        db=db_session,
        preset="bobs-inspired",
        seed=11,
        n_blend_samples=4,
        n_process_samples=3,
        top=2,
        candidates=candidates,
        notes="first DB-backed run",
        git_commit="testcommit",
    )

    runs = list_saved_runs(db_session)
    assert runs[0].id == run.id
    assert runs[0].preset == "bobs-inspired"
    assert len(runs[0].candidates) == 2
    assert json.loads(runs[0].candidates[0].proportions)

    marked = mark_candidate(
        db=db_session,
        candidate_id=runs[0].candidates[0].id,
        status="test_next",
        notes="promising protein and viscosity",
    )
    assert marked.status == "test_next"
    assert marked.decision_notes == "promising protein and viscosity"


def test_save_application_run(db_session):
    _seed_ingredients(db_session)
    _seed_applications(db_session)
    db_session.commit()

    result = rank_application_candidates(
        application="Pane",
        bounds=PRESETS["bobs-inspired"],
        n_blend_samples=10,
        n_process_samples=5,
        top=2,
        seed=11,
        db=db_session,
    )

    run = save_application_run(
        db=db_session,
        result=result,
        preset="bobs-inspired",
        seed=11,
        n_blend_samples=10,
        n_process_samples=5,
        top=2,
        notes="general application run",
        git_commit="testcommit",
    )

    assert run.source == "cli.rank-application"
    assert run.application_name == "Pane"
    assert len(run.candidates) == 2
    assert json.loads(run.candidates[0].metrics)["specific_volume_cm3_g"] > 0


def test_cli_cohort_analyze_writes_json(db_session, monkeypatch, tmp_path):
    _seed_ingredients(db_session)
    _seed_applications(db_session)
    db_session.commit()
    candidates = rank_pane_candidates(
        preset="bobs-inspired",
        n_blend_samples=4,
        n_process_samples=3,
        top=2,
        seed=12,
        db=db_session,
    )
    run = save_pane_run(
        db=db_session,
        preset="bobs-inspired",
        seed=12,
        n_blend_samples=4,
        n_process_samples=3,
        top=2,
        candidates=candidates,
        git_commit="testcommit",
    )
    monkeypatch.setattr(cli_mod, "_persistent_session", lambda: db_session)
    output_path = tmp_path / "cohort.json"

    exit_code = main([
        "cohort",
        "analyze",
        "--application",
        "Pane",
        "--preset",
        "bobs-inspired",
        "--max-rank",
        "2",
        "--json",
        str(output_path),
    ])

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["candidate_count"] == 2
    assert payload["run_count"] == 1
    assert payload["preset_counts"] == {"bobs-inspired": 2}
    assert payload["top_candidates"][0]["run_id"] == run.id
    assert "Sorghum flour" in payload["ingredients"]


def test_cli_sensitivity_analyze_writes_json(db_session, monkeypatch, tmp_path):
    _seed_ingredients(db_session)
    _seed_applications(db_session)
    db_session.commit()
    candidates = rank_pane_candidates(
        preset="bobs-inspired",
        n_blend_samples=4,
        n_process_samples=3,
        top=1,
        seed=13,
        db=db_session,
    )
    run = save_pane_run(
        db=db_session,
        preset="bobs-inspired",
        seed=13,
        n_blend_samples=4,
        n_process_samples=3,
        top=1,
        candidates=candidates,
        git_commit="testcommit",
    )
    candidate_id = run.candidates[0].id
    monkeypatch.setattr(cli_mod, "_persistent_session", lambda: db_session)
    output_path = tmp_path / "sensitivity.json"

    exit_code = main([
        "sensitivity",
        "analyze",
        "--application",
        "Pane",
        "--candidate-id",
        str(candidate_id),
        "--perturb",
        "Pea protein powder:0.005",
        "--compensate-with",
        "Sorghum flour",
        "--process-samples",
        "3",
        "--seed",
        "13",
        "--json",
        str(output_path),
    ])

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["application"] == "Pane"
    assert payload["base"]["score"] > 0
    assert len(payload["variants"]) == 1
    assert payload["variants"][0]["perturbation"]["ingredient"] == "Pea protein powder"
    assert "properties.protein_pct" in payload["variants"][0]["deltas"]


def test_cli_flavor_explain_writes_json(db_session, monkeypatch, tmp_path):
    _seed_ingredients(db_session)
    _seed_applications(db_session)
    db_session.commit()
    candidates = rank_pane_candidates(
        preset="bobs-inspired",
        n_blend_samples=4,
        n_process_samples=3,
        top=1,
        seed=14,
        db=db_session,
    )
    run = save_pane_run(
        db=db_session,
        preset="bobs-inspired",
        seed=14,
        n_blend_samples=4,
        n_process_samples=3,
        top=1,
        candidates=candidates,
        git_commit="testcommit",
    )
    candidate_id = run.candidates[0].id
    monkeypatch.setattr(cli_mod, "_persistent_session", lambda: db_session)
    output_path = tmp_path / "flavor.json"

    exit_code = main([
        "flavor",
        "explain",
        "--application",
        "Pane",
        "--candidate-id",
        str(candidate_id),
        "--json",
        str(output_path),
    ])

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["target"]["name"] == "Pane"
    assert payload["flavor_score"] > 0
    assert payload["contributions"]
    assert payload["interpretation"]


def test_cli_candidate_report_writes_markdown(db_session, monkeypatch, tmp_path):
    _seed_ingredients(db_session)
    _seed_applications(db_session)
    db_session.commit()
    candidates = rank_pane_candidates(
        preset="bobs-inspired",
        n_blend_samples=4,
        n_process_samples=3,
        top=1,
        seed=15,
        db=db_session,
    )
    run = save_pane_run(
        db=db_session,
        preset="bobs-inspired",
        seed=15,
        n_blend_samples=4,
        n_process_samples=3,
        top=1,
        candidates=candidates,
        git_commit="testcommit",
    )
    candidate = mark_candidate(
        db=db_session,
        candidate_id=run.candidates[0].id,
        status="test_next",
        notes="selected for dossier test",
    )
    monkeypatch.setattr(cli_mod, "_persistent_session", lambda: db_session)
    output_path = tmp_path / "candidate-report.md"

    exit_code = main([
        "candidates",
        "report",
        str(candidate.id),
        "--markdown",
        str(output_path),
    ])

    assert exit_code == 0
    markdown = output_path.read_text(encoding="utf-8")
    assert f"# Candidate #{candidate.id} Dossier" in markdown
    assert "## Formula" in markdown
    assert "## Predicted Metrics" in markdown
    assert "## Confidence And Evidence Notes" in markdown
    assert "## Flavor Explanation" in markdown
    assert "primary physical-test candidate" in markdown
    assert "Treat all predictions as pre-lab hypotheses" in markdown


def test_cli_candidate_report_rejects_missing_candidate(db_session, monkeypatch):
    monkeypatch.setattr(cli_mod, "_persistent_session", lambda: db_session)

    with pytest.raises(SystemExit, match="Simulation candidate not found: 999"):
        main(["candidates", "report", "999"])


def test_cli_candidate_protocol_writes_markdown(db_session, monkeypatch, tmp_path):
    _seed_ingredients(db_session)
    _seed_applications(db_session)
    db_session.commit()
    candidates = rank_pane_candidates(
        preset="bobs-inspired",
        n_blend_samples=4,
        n_process_samples=3,
        top=1,
        seed=16,
        db=db_session,
    )
    run = save_pane_run(
        db=db_session,
        preset="bobs-inspired",
        seed=16,
        n_blend_samples=4,
        n_process_samples=3,
        top=1,
        candidates=candidates,
        git_commit="testcommit",
    )
    candidate_id = run.candidates[0].id
    monkeypatch.setattr(cli_mod, "_persistent_session", lambda: db_session)
    output_path = tmp_path / "candidate-protocol.md"

    exit_code = main([
        "candidates",
        "protocol",
        str(candidate_id),
        "--batch-g",
        "500",
        "--markdown",
        str(output_path),
    ])

    assert exit_code == 0
    markdown = output_path.read_text(encoding="utf-8")
    assert f"# Physical-Test Protocol: Candidate #{candidate_id}" in markdown
    assert "| **Total dry blend** | **100.00%** | **500.00** |" in markdown
    assert "specific_volume_cm3_g" in markdown
    assert "crumb_hardness_n" in markdown
    assert "water_added_g" in markdown
    assert "This protocol does not validate the candidate by itself." in markdown


def test_cli_candidate_protocol_rejects_invalid_batch(db_session, monkeypatch):
    monkeypatch.setattr(cli_mod, "_persistent_session", lambda: db_session)

    with pytest.raises(SystemExit, match="batch_g must be positive"):
        main(["candidates", "protocol", "1", "--batch-g", "0"])


def test_cli_coverage_gaps_writes_candidate_json(db_session, monkeypatch, tmp_path):
    _seed_ingredients(db_session)
    _seed_applications(db_session)
    db_session.commit()
    candidates = rank_pane_candidates(
        preset="bobs-inspired",
        n_blend_samples=4,
        n_process_samples=3,
        top=1,
        seed=17,
        db=db_session,
    )
    run = save_pane_run(
        db=db_session,
        preset="bobs-inspired",
        seed=17,
        n_blend_samples=4,
        n_process_samples=3,
        top=1,
        candidates=candidates,
        git_commit="testcommit",
    )
    candidate_id = run.candidates[0].id
    monkeypatch.setattr(cli_mod, "_persistent_session", lambda: db_session)
    output_path = tmp_path / "coverage-gaps.json"

    exit_code = main([
        "coverage",
        "gaps",
        "--application",
        "Pane",
        "--candidate-id",
        str(candidate_id),
        "--json",
        str(output_path),
    ])

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["application"] == "Pane"
    assert payload["domain"] == "bread_baking"
    assert payload["summary"]["record_count"] > 0
    assert "specific_volume_cm3_g" in payload["expected_metrics"]
    assert payload["candidate"]["candidate_id"] == candidate_id
    assert payload["candidate"]["assessment"]["level"] in {"low", "medium", "high"}


def test_cli_feedback_summary_writes_json(db_session, monkeypatch, tmp_path):
    _seed_ingredients(db_session)
    _seed_applications(db_session)
    db_session.commit()
    candidates = rank_pane_candidates(
        preset="bobs-inspired",
        n_blend_samples=4,
        n_process_samples=3,
        top=1,
        seed=18,
        db=db_session,
    )
    run = save_pane_run(
        db=db_session,
        preset="bobs-inspired",
        seed=18,
        n_blend_samples=4,
        n_process_samples=3,
        top=1,
        candidates=candidates,
        git_commit="testcommit",
    )
    candidate = run.candidates[0]
    blend = Blend(name="feedback test blend", application_id=run.application_id)
    db_session.add(blend)
    db_session.flush()
    db_session.add(ExperimentResult(
        blend_id=blend.id,
        application_id=run.application_id,
        conditions=json.dumps({"candidate_id": candidate.id, "dry_blend_g": 500}),
        metrics=json.dumps({
            "specific_volume_cm3_g": 2.5,
            "crumb_hardness_n": 10.0,
            "unmatched_numeric": 42,
            "notes": "good handling",
        }),
    ))
    db_session.commit()
    monkeypatch.setattr(cli_mod, "_persistent_session", lambda: db_session)
    output_path = tmp_path / "feedback-summary.json"

    exit_code = main([
        "feedback",
        "summary",
        "--application",
        "Pane",
        "--json",
        str(output_path),
    ])

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "compared"
    assert payload["linked_experiment_count"] == 1
    assert payload["comparison_count"] == 2
    metrics = {row["metric"]: row for row in payload["metrics"]}
    assert "specific_volume_cm3_g" in metrics
    assert metrics["specific_volume_cm3_g"]["count"] == 1
    assert payload["candidates"][0]["candidate_id"] == candidate.id
    assert payload["unmatched_measurements"] == {"unmatched_numeric": 1}


def test_cli_feedback_summary_handles_empty_data(db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(cli_mod, "_persistent_session", lambda: db_session)
    output_path = tmp_path / "feedback-empty.json"

    exit_code = main(["feedback", "summary", "--application", "Pane", "--json", str(output_path)])

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "no_experiments"
    assert payload["metrics"] == []


def test_cli_experiments_record_links_candidate_feedback(db_session, monkeypatch, tmp_path):
    _seed_ingredients(db_session)
    _seed_applications(db_session)
    db_session.commit()
    candidates = rank_pane_candidates(
        preset="bobs-inspired",
        n_blend_samples=4,
        n_process_samples=3,
        top=1,
        seed=19,
        db=db_session,
    )
    run = save_pane_run(
        db=db_session,
        preset="bobs-inspired",
        seed=19,
        n_blend_samples=4,
        n_process_samples=3,
        top=1,
        candidates=candidates,
        git_commit="testcommit",
    )
    candidate = run.candidates[0]
    candidate_id = candidate.id
    run_id = run.id
    monkeypatch.setattr(cli_mod, "_persistent_session", lambda: db_session)

    exit_code = main([
        "experiments",
        "record",
        "--candidate-id",
        str(candidate_id),
        "--metric",
        "specific_volume_cm3_g:2.45",
        "--metric",
        "crumb_hardness_n:11.2",
        "--condition",
        "dry_blend_g:500",
        "--condition",
        "operator:lab-a",
        "--notes",
        "first CLI record",
    ])

    assert exit_code == 0
    experiment = db_session.query(ExperimentResult).one()
    conditions = json.loads(experiment.conditions)
    metrics = json.loads(experiment.metrics)
    assert conditions["candidate_id"] == candidate_id
    assert conditions["simulation_run_id"] == run_id
    assert conditions["dry_blend_g"] == 500
    assert conditions["operator"] == "lab-a"
    assert conditions["notes"] == "first CLI record"
    assert metrics["specific_volume_cm3_g"] == 2.45

    output_path = tmp_path / "feedback-after-record.json"
    exit_code = main([
        "feedback",
        "summary",
        "--application",
        "Pane",
        "--json",
        str(output_path),
    ])

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "compared"
    assert payload["linked_experiment_count"] == 1
    assert payload["comparison_count"] == 2


def test_cli_candidate_feedback_writes_json(db_session, monkeypatch, tmp_path):
    _seed_ingredients(db_session)
    _seed_applications(db_session)
    db_session.commit()
    candidates = rank_pane_candidates(
        preset="bobs-inspired",
        n_blend_samples=4,
        n_process_samples=3,
        top=1,
        seed=20,
        db=db_session,
    )
    run = save_pane_run(
        db=db_session,
        preset="bobs-inspired",
        seed=20,
        n_blend_samples=4,
        n_process_samples=3,
        top=1,
        candidates=candidates,
        git_commit="testcommit",
    )
    candidate_id = run.candidates[0].id
    monkeypatch.setattr(cli_mod, "_persistent_session", lambda: db_session)
    main([
        "experiments",
        "record",
        "--candidate-id",
        str(candidate_id),
        "--metric",
        "specific_volume_cm3_g:2.45",
        "--metric",
        "crumb_hardness_n:11.2",
        "--condition",
        "dry_blend_g:500",
    ])
    output_path = tmp_path / "candidate-feedback.json"

    exit_code = main([
        "candidates",
        "feedback",
        str(candidate_id),
        "--json",
        str(output_path),
    ])

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["candidate_id"] == candidate_id
    assert payload["experiment_count"] == 1
    assert payload["summary"]["status"] == "compared"
    compared_metrics = {row["metric"] for row in payload["comparisons"]}
    assert {"specific_volume_cm3_g", "crumb_hardness_n"}.issubset(compared_metrics)


def test_cli_candidate_feedback_rejects_missing_candidate(db_session, monkeypatch):
    monkeypatch.setattr(cli_mod, "_persistent_session", lambda: db_session)

    with pytest.raises(SystemExit, match="Simulation candidate not found: 999"):
        main(["candidates", "feedback", "999"])


def test_cli_lab_package_writes_candidate_artifacts(db_session, monkeypatch, tmp_path):
    _seed_ingredients(db_session)
    _seed_applications(db_session)
    db_session.commit()
    candidates = rank_pane_candidates(
        preset="bobs-inspired",
        n_blend_samples=4,
        n_process_samples=3,
        top=1,
        seed=21,
        db=db_session,
    )
    run = save_pane_run(
        db=db_session,
        preset="bobs-inspired",
        seed=21,
        n_blend_samples=4,
        n_process_samples=3,
        top=1,
        candidates=candidates,
        git_commit="testcommit",
    )
    candidate_id = run.candidates[0].id
    monkeypatch.setattr(cli_mod, "_persistent_session", lambda: db_session)
    output_dir = tmp_path / "lab-package"

    exit_code = main([
        "lab",
        "package",
        "--candidate-id",
        str(candidate_id),
        "--output-dir",
        str(output_dir),
        "--batch-g",
        "500",
    ])

    assert exit_code == 0
    index = (output_dir / "index.md").read_text(encoding="utf-8")
    report = (output_dir / f"candidate-{candidate_id}-report.md").read_text(encoding="utf-8")
    protocol = (output_dir / f"candidate-{candidate_id}-protocol.md").read_text(encoding="utf-8")
    record_command = (output_dir / f"candidate-{candidate_id}-record-command.md").read_text(encoding="utf-8")
    assert f"candidate-{candidate_id}-report.md" in index
    assert f"# Candidate #{candidate_id} Dossier" in report
    assert f"# Physical-Test Protocol: Candidate #{candidate_id}" in protocol
    assert f"uv run glutenix experiments record --candidate-id {candidate_id}" in record_command
    assert "--metric specific_volume_cm3_g:VALUE" in record_command
    assert f"uv run glutenix candidates feedback {candidate_id}" in record_command


def test_cli_lab_package_rejects_missing_candidate(db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(cli_mod, "_persistent_session", lambda: db_session)
    output_dir = tmp_path / "missing-package"

    with pytest.raises(SystemExit, match="Simulation candidate not found: 999"):
        main([
            "lab",
            "package",
            "--candidate-id",
            "999",
            "--output-dir",
            str(output_dir),
        ])
    assert not output_dir.exists()


def test_cli_experiments_record_rejects_missing_candidate(db_session, monkeypatch):
    monkeypatch.setattr(cli_mod, "_persistent_session", lambda: db_session)

    with pytest.raises(SystemExit, match="Simulation candidate not found: 999"):
        main([
            "experiments",
            "record",
            "--candidate-id",
            "999",
            "--metric",
            "specific_volume_cm3_g:2.45",
        ])
