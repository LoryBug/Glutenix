import json

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
