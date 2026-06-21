# Digital Campaigns

Digital campaigns are reproducible screening runs that aggregate candidate behavior into formulation families, risk patterns, and evidence-coverage diagnostics. They are not experimental validation and they do not rank a formulation as an instruction to make or test.

## Specification Format

Campaign specs use Python dataclasses in `glutenix.analysis.campaigns` with format version `digital-campaigns-v1`.

Each spec includes:

- `application`: food category passed to the application-aware optimizer.
- `sweep_axes`: variables, values, control status, and notes.
- `variants`: preset or ingredient bounds, fixed seed, sample counts, process bounds, and family label.
- `gap_notes`: explicit limitations that affect interpretation.
- `output_requirements`: checks that each report must satisfy.

This uses Python rather than YAML to avoid adding a parsing dependency and to reuse existing `IngredientBound` and `ProcessBounds` types.

## Reproduce Reports

Generate all campaign reports:

```bash
uv run python scripts/run_digital_campaigns.py --date 2026-06-21
```

Check committed reports for freshness:

```bash
uv run python scripts/run_digital_campaigns.py --date 2026-06-21 --check
```

Run a small validation pass without writing files:

```bash
uv run python scripts/run_digital_campaigns.py --dry-run
```

## Interpretation Rules

- Treat robust families as stable digital patterns, not as validated recipes.
- Read confidence summaries and risk flags before scores.
- For Pizza V1, require audit-boundary coverage diagnostics because no structured pizza calibration dataset exists.
- Report unsupported variables honestly as gaps instead of forcing a formulation family.
