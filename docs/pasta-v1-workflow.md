# Pasta V1 Workflow

Pasta fresca is the second Glutenix application workflow. It is `experimental_v1`: the system can rank candidate formulas with pasta-specific metrics, but the results are still heuristic and require cooking tests.

## Command

```bash
uv run glutenix rank-application --application "Pasta fresca" --preset pasta-rice-structure-v1 --blend-samples 100 --process-samples 20 --top 10 --seed 42
```

Use `--save-run` when the campaign should become part of the scientific history.

## Preset

`pasta-rice-structure-v1` is a rice/starch-network search space intended for a first fresh pasta workflow:

- High-amylose rice flour: 45-65%
- Brown rice flour: 12-28%
- Sweet rice flour (Mochiko): 8-22%
- Soy protein isolate: 3-8%
- Sodium alginate: 0.8-1.8%
- Konjac glucomannan: 0.5-2.0%
- Curdlan: 0.5-2.0%

The preset is designed to explore amylose/protein/hydrocolloid structure. It is not a validated formula.

## Primary Metrics

Pasta V1 uses pasta-specific metrics:

- `cooking_loss_pct`: lower is better.
- `firmness_index`: target is moderate-high firmness without over-hardness.
- `water_uptake_pct`: model-predicted water uptake during cooking.
- `protein_pct`: nutritional/protein contribution from the dry blend.

Do not interpret bread metrics such as loaf volume or crumb hardness as pasta outcomes.

## Current Assumptions

- The ranking path uses `PastaCookingSimulator`, not the bread simulator.
- Process search is mapped to cooking water temperature and cooking time.
- When sodium alginate is present, the current CLI path uses a calcium-alginate fresh-pasta starting point: `water_temp_c=100.0`, `water_to_flour_ratio=3.0`, `calcium_lactate_m=0.1`, and `calcium_bath_time_min=30.0`.
- Non-alginate pasta formulas fall back to generic fresh-pasta assumptions.
- Flavor fit remains heuristic and not sensory-panel calibrated.

## Evidence Limits

- Literature coverage for pasta is narrower than the Pane workflow.
- Some literature uses `water_absorption_pct`; Glutenix V1 records the simulator output as `water_uptake_pct` for prediction-feedback consistency.
- Calcium-alginate process settings are literature-aligned starting assumptions, not validated lab instructions for every formula.
- The first Pasta candidates should be treated as hypotheses for cooking tests, not validated recipes.

## Next Lab Measurements

When a Pasta candidate is physically tested, record:

- cooking time and water temperature actually used
- water-to-flour ratio and calcium bath conditions if used
- dry pasta/formula mass
- cooked mass or water uptake
- cooking loss in cooking water
- firmness/texture method and result
- protein if measured or analytically calculated
- sensory notes: starchiness, gumminess, bitterness, beany/soy note, surface stickiness
