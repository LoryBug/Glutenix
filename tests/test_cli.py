import json

import pytest

import glutenix.cli as cli_mod
from glutenix.cli import (
    PRESETS,
    list_saved_runs,
    main,
    mark_candidate,
    rank_application_candidates,
    rank_pane_candidates,
    save_application_run,
    save_pane_run,
)
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


def test_pane_presets_reference_seeded_ingredient_names():
    assert {"sorghum-baseline", "bobs-inspired", "schaer-inspired"}.issubset(PRESETS)


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
