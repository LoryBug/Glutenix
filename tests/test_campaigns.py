from pathlib import Path

from glutenix.analysis.campaigns import campaign_specs, planned_campaign_outputs, render_campaign_report


def test_campaign_specs_define_required_categories():
    specs = campaign_specs(sample_mode="dry-run")

    assert set(specs) == {"bread", "pasta", "pizza"}
    for spec in specs.values():
        assert spec.sweep_axes
        assert spec.variants
        assert spec.output_requirements


def test_dry_run_campaign_report_contains_required_sections():
    spec = campaign_specs(sample_mode="dry-run")["pizza"]

    report = render_campaign_report(spec, report_date="2099-01-01")

    assert "## Reproducibility" in report
    assert "## Robust Formulation Families" in report
    assert "## Risk Pattern Analysis" in report
    assert "## Coverage Diagnostics" in report
    assert "not experimental validation" in report
    assert "best formulation" not in report.lower()
    assert "recommendation" not in report.lower()


def test_planned_campaign_outputs_are_reproducible_paths():
    outputs = planned_campaign_outputs(
        output_dir=Path("docs/campaigns"),
        report_date="2099-01-01",
        campaign="bread",
        sample_mode="dry-run",
    )

    assert list(outputs) == [Path("docs/campaigns/bread-2099-01-01.md")]
    assert "uv run python scripts/run_digital_campaigns.py --campaign bread --date 2099-01-01" in next(iter(outputs.values()))
