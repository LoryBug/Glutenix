# Target Profile Calibration

Glutenix currently optimizes process parameters with application-specific target profiles. These profiles are intentionally marked as `heuristic`: they combine literature-informed ranges, standard baking/process knowledge, and outputs from the internal physics engine. They are not yet calibrated against controlled lab experiments.

## Current Data Sources

- `docs/application-targets-research.md`: working literature notes and extracted ranges for pizza, bread, biscuits/cookies, shortcrust, fresh pasta, and sweet leavened products.
- `glutenix/engine/blend.py`: computed blend properties such as water absorption, gelatinization range, viscosity index, hydrocolloid percentage, and nutritional weighted averages.
- `glutenix/engine/fermentation.py`: simulated fermentation volume increase.
- `glutenix/engine/baking.py`: simulated core and crust temperatures.
- `glutenix/engine/targets.py`: explicit target profiles used by sweep scoring.

## Current Status

The optimizer ranks process combinations by comparing simulated outputs with target values:

- `volume_target`: desired volume increase for the product style.
- `core_target_c`: desired core temperature, usually tied to complete starch gelatinization and safe/finished bake.
- `crust_target_c`: desired surface/crust temperature proxy for browning or crispness.
- `efficiency_start_min` and `efficiency_window_min`: soft penalty for unnecessarily long processes.

The score is useful for exploration, but should not be interpreted as experimentally validated quality prediction yet.

## Calibration Plan

1. Define a controlled experiment template for each product family.
2. Run a designed set of blends and process conditions, not only random trials.
3. Store measured results in `experiment_results` with structured JSON metrics.
4. Compare measured metrics against physics simulation outputs.
5. Fit correction factors or update target sigmas per application.
6. Promote a profile from `heuristic` to `calibrated` only when backed by repeated experiments.

## Suggested Experimental Metrics

- `volume_increase_pct`: measured after fermentation and/or final bake.
- `specific_volume_ml_g`: especially for bread and sweet leavened products.
- `core_temp_c`: measured immediately after bake.
- `crust_color_l_a_b` or a simpler browning score.
- `hardness_n`: texture analyzer or consistent proxy.
- `moisture_pct`: crumb or product moisture.
- `sensory_score`: structured panel score, even if small.
- `failure_notes`: collapse, gummy crumb, cracking, poor shape hold.

## Minimum Calibration Dataset

For each application, start with:

- 3 to 5 representative blends.
- 8 to 12 process points per blend.
- At least 2 repeated runs for the best candidates.

This gives enough signal to estimate whether target centers and sigmas are realistic before training a more formal quality model.

## Next Implementation Steps

- Add a structured experiment import/export format.
- Add a calibration report endpoint that compares simulated vs measured metrics.
- Add per-profile `calibration_status`, `n_experiments`, and error metrics.
- Let `targets.py` load profiles from a JSON/YAML file once the profile format stabilizes.
