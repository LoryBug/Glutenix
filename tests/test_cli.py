import json

from glutenix.cli import PRESETS, main, rank_pane_candidates


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


def test_pane_presets_reference_seeded_ingredient_names():
    assert {"sorghum-baseline", "bobs-inspired", "schaer-inspired"}.issubset(PRESETS)
