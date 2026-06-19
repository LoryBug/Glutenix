from glutenix.engine.confidence import assess_candidate_confidence
from glutenix.engine.targets import get_sweep_target_profile


class TestCandidateConfidence:
    def test_flags_out_of_range_candidate(self):
        profile = get_sweep_target_profile("Pizza")

        confidence = assess_candidate_confidence(
            blend_values={
                "water_absorption": 3.5,
                "viscosity_index": 0.4,
                "hydrocolloid_pct": 0.08,
                "fiber_pct": 14.0,
                "fat_pct": 0.1,
            },
            profile=profile,
            process_score=0.3,
            blend_score=0.2,
            flavor_score=0.4,
        )

        assert confidence.level == "low"
        assert confidence.score < 0.5
        assert confidence.risk_flags
        assert any("water_absorption" in flag for flag in confidence.risk_flags)
        assert any("Process score is weak" in flag for flag in confidence.risk_flags)

    def test_uses_pasta_calibration_score(self):
        profile = get_sweep_target_profile("Pasta fresca")

        confidence = assess_candidate_confidence(
            blend_values={
                "water_absorption": 1.2,
                "viscosity_index": 1.8,
                "hydrocolloid_pct": 0.015,
                "protein_pct": 10.0,
                "amylose_pct": 22.0,
            },
            profile=profile,
            process_score=0.85,
            blend_score=0.9,
            flavor_score=0.82,
            cooking_metrics={
                "calibration_score": 0.85,
                "calibration_confidence": "high",
            },
        )

        assert confidence.level == "high"
        assert confidence.score >= 0.75
        assert not confidence.risk_flags
        assert any("Pasta cooking model" in note for note in confidence.basis)

    def test_includes_literature_coverage_warnings(self):
        profile = get_sweep_target_profile("Pane")

        confidence = assess_candidate_confidence(
            blend_values={
                "water_absorption": 4.0,
                "viscosity_index": 0.5,
                "hydrocolloid_pct": 0.0,
                "protein_pct": 4.0,
            },
            profile=profile,
            process_score=0.7,
            blend_score=0.7,
            flavor_score=0.7,
            literature_coverage={
                "score": 0.2,
                "level": "low",
                "basis": [],
                "risk_flags": ["Process 'hydration_pct' is below literature coverage."],
            },
        )

        assert confidence.score < 0.7
        assert any("Literature coverage/OOD confidence: low" in note for note in confidence.basis)
        assert any("hydration_pct" in flag for flag in confidence.risk_flags)
