# Literature Extraction Template

Use this template before adding a paper to `data/literature/*.jsonl`. The goal is to preserve traceability from the paper table/figure to model inputs.

## Source

- Title:
- Authors:
- Year:
- DOI:
- PMCID/URL:
- Product/application:
- Table/figure used:

## Experimental Context

- Ingredient system:
- Process summary:
- Critical conditions:
- Replicates/statistics:
- Notes on units:

## Extracted Metrics

| Record ID | Formula | Process | Metric | Mean | SD/SE | Unit | Source location | Notes |
|---|---|---|---|---:|---:|---|---|---|
| `paper_year_condition_metric` |  |  |  |  |  |  |  |  |

## Glutenix Mapping

| Literature ingredient | Glutenix ingredient | Mapping type | Rationale | Risk |
|---|---|---|---|---|
|  |  | direct/proxy/missing |  | low/medium/high |

## JSONL Record Shape

Each line in a literature dataset is one observation.

```json
{
  "id": "lux_2023_r1_10_alg1_5_10min",
  "application": "Pasta fresca",
  "source": {
    "title": "Physical quality of gluten-free doughs and fresh pasta made of amaranth",
    "doi": "10.1002/fsn3.3301",
    "pmcid": "PMC10261804",
    "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10261804/",
    "table": "Table 2b"
  },
  "literature_formula": {
    "amaranth_flour": 0.985,
    "sodium_alginate": 0.015
  },
  "mapped_formula": {
    "Amaranth flour": 0.985,
    "Sodium alginate": 0.015
  },
  "mapping_notes": "Direct mapping; original formulation used amaranth flour:water 1:10 and 1.5 wt% alginate on flour basis.",
  "process": {
    "water_temp_c": 100.0,
    "cooking_time_min": 10.0,
    "pasta_thickness_mm": 2.0,
    "flour_water_ratio": "1:10",
    "calcium_lactate_m": 0.1,
    "calcium_bath_time_min": 30.0,
    "dough_heat_temp_c": 80.0,
    "dough_heat_time_min": 60.0,
    "dried_pasta": false,
    "extrusion_moisture_pct": null
  },
  "measured": {
    "cooking_loss_pct": 1.19,
    "water_absorption_pct": -4.68,
    "swelling_index": 8.91
  },
  "confidence": "high"
}
```

## Validation Rules

- `id`, `application`, `source.title`, `literature_formula`, `mapped_formula`, `process.cooking_time_min`, `measured.cooking_loss_pct`, and `confidence` are required.
- `source` must include at least one of `doi`, `pmcid`, or `url`.
- `mapped_formula` must sum to `1.0`.
- Formula values must be positive finite numbers.
- `cooking_loss_pct` must be non-negative.
- `confidence` must be `low`, `medium`, or `high`.
- Use `flour_water_ratio` as text like `1:10` when the paper reports flour:water directly; the calibration loader converts it to `water_to_flour_ratio`.
- Keep process water separate from `mapped_formula`; mapped formulas are normalized over dry/solid ingredients.
- Use `dried_pasta: true` for dried extruded pasta systems; if the paper reports `M2/M1*100` water absorption, store the net uptake in `water_absorption_pct` and the original value in `water_absorption_total_pct`.

## Confidence Guide

- `high`: direct table value with clear units and direct ingredient mapping.
- `medium`: value manually extracted from a figure or uses a close ingredient/process proxy.
- `low`: value inferred from text, partial formula information, or substantial proxy mapping.

## Before Committing

Run:

```powershell
uv run pytest tests/test_calibration.py -q
```
