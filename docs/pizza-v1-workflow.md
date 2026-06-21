# Pizza V1 Workflow

Pizza V1 is a conservative digital screening workflow for gluten-free pizza-like doughs. It is not a calibrated pizza simulator and it is not a recipe generator.

The evidence boundary is defined in `docs/pizza-v1-literature-audit.md`. Candidate outputs should be interpreted through `model_confidence` and `coverage_diagnostics`, not through score alone.

## CLI Usage

```bash
uv run glutenix rank-application \
  --application Pizza \
  --preset pizza-v1 \
  --blend-samples 100 \
  --process-samples 20 \
  --top 10 \
  --seed 42
```

The `pizza-v1` preset uses only seeded ingredients compatible with the current audit boundary: rice flour, sorghum flour, tapioca starch, corn starch, psyllium, HPMC, and xanthan gum. Lentil flour is documented in the audit but is not part of the executable preset until an ingredient entry exists.

## Evidence Diagnostics

Pizza V1 candidates include:

- `coverage_diagnostics.coverage_fraction`: fraction of assessed Pizza V1 variables inside audited boundaries.
- `coverage_diagnostics.variable_diagnostics`: per-variable `in_range`, `out_of_range`, or `unsupported` status.
- `coverage_diagnostics.risk_flags`: evidence-boundary warnings.
- `model_confidence.confidence_summary`: conservative candidate confidence tier.

Any out-of-range Pizza V1 diagnostic should be treated as extrapolation. A high ranking score means only that the candidate scores well under current heuristics; it does not mean the formula is experimentally validated.

## Standalone Coverage Check

Saved Pizza candidates can be inspected with:

```bash
uv run glutenix coverage gaps --application Pizza --candidate-id CANDIDATE_ID
```

This reports Pizza V1 audit-boundary diagnostics. It does not report calibration error because no structured pizza calibration dataset exists yet.

## Limits

- No `data/literature/pizza_baking.jsonl` dataset exists yet.
- No pizza calibration endpoint exists yet.
- No claims are made about optimality, sensory acceptability, or lab performance.
- High-temperature Neapolitan-style baking, cold fermentation, sourdough, commercial mixes, and unsupported proteins remain outside Pizza V1 evidence boundaries.
