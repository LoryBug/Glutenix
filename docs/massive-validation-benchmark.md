# Massive Validation Benchmark

Public working note: this is a historical simulation benchmark, not experimental validation and not a generated report with freshness checks yet.

Date: 2026-06-18

Purpose: stress-test the current Glutenix heuristic models across several product applications before deciding which candidates deserve real lab trials.

This is not experimental validation yet. It is a simulation and plausibility benchmark against the target ranges documented in `docs/application-targets-research.md`, the calibration plan in `docs/target-profile-calibration.md`, and the sensory proxy in `docs/flavor-heuristic-model.md`.

## Method

Applications tested:

- Pizza
- Pane
- Lievitati dolci
- Frolla
- Pasta fresca
- Biscotti

Sampling design:

- 80 random bounded blend candidates per application.
- 12 random process points per blend.
- 6 applications x 80 blends x 12 process points = 5,760 simulated process evaluations.

Score weighting:

```text
total_score = 0.50 process_score + 0.25 functional_blend_score + 0.25 flavor_score
```

The benchmark checked:

- Process match: volume increase, core temperature, crust temperature, time efficiency.
- Functional blend match: water absorption, viscosity index, hydrocolloid percentage, fiber/fat/protein/starch/amylose where relevant.
- Flavor proxy match: neutral, cereal, nutty, earthy, bitter, sweet, toasted, rich.

## Online Evidence Anchors

The target ranges are currently linked to the online/literature notes already collected in `docs/application-targets-research.md`.

Examples of extracted evidence anchors:

- Gluten-free pizza/bread/pasta/cookies literature notes with DOI/PMCID links.
- HPMC/xanthan/guar/psyllium ranges for structure and volume.
- Cookie hardness and spread ratio studies.
- Pasta cooking loss and firmness studies.
- Bread specific volume and crumb firmness studies.

Important limitation: the current benchmark compares simulated outputs to these ranges, but does not yet fit model parameters directly against the numerical paper datasets.

## Summary Results

| Application | Candidates | Top Score | Median Score | Top Process | Top Blend | Top Flavor | Avg Top Range Hit | Main Observation |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Pizza | 80 | 0.932 | 0.874 | 0.938 | 0.936 | 0.915 | 1.00 | Coherent top candidates |
| Pane | 80 | 0.878 | 0.837 | 0.838 | 0.876 | 0.961 | 0.94 | Coherent, but volume target remains hard |
| Lievitati dolci | 80 | 0.862 | 0.830 | 0.813 | 0.951 | 0.870 | 1.00 | Functional/flavor plausible, volume too low |
| Frolla | 80 | 0.928 | 0.861 | 0.942 | 0.938 | 0.891 | 1.00 | Coherent top candidates |
| Pasta fresca | 80 | 0.727 | 0.688 | 0.548 | 0.843 | 0.969 | 0.82 | Process model not appropriate yet |
| Biscotti | 80 | 0.921 | 0.862 | 0.910 | 0.951 | 0.913 | 1.00 | Coherent top candidates |

## Key Findings

### 1. Pizza Model Looks Plausible

Best pizza candidates land in the expected functional windows:

| Metric | Target Range | Median Top-10 | Status |
|---|---:|---:|---|
| fat_pct | 0.5-6 | 1.59 | OK |
| fiber_pct | 2-8 | 4.40 | OK |
| hydrocolloid_pct | 1-4% | 2.98% | OK |
| viscosity_index | 1.4-2.8 | 1.73 | OK |
| water_absorption | 1.2-1.9 | 1.61 | OK |

Top pizza candidate:

```text
Score: 0.932
Volume: +66.6%
Core: 90.8C
Crust: 198.6C
Process: fermentation 31.6C / 177 min; bake 240.5C / 33 min
Blend: sorghum 42.5%, potato starch 26.7%, white rice 15.8%, tapioca 11.7%, hydrocolloids remainder
```

Interpretation: the model converges on blends that look reasonable for gluten-free pizza: moderate/high starch, sorghum for cereal character and structure, and hydrocolloids in a realistic range.

Main weakness: flavor target wants more `cereal` and `toasted` character than the raw ingredient proxy predicts. This may be partially resolved by real baking aroma, which is not modeled yet.

### 2. Bread Is Functionally Coherent But Volume Is Underpowered

Top bread candidates hit most functional ranges:

| Metric | Target Range | Median Top-10 | Status |
|---|---:|---:|---|
| fiber_pct | 3-10 | 5.58 | OK |
| hydrocolloid_pct | 1.5-5% | 3.15% | OK |
| protein_pct | 5-12 | 5.77 | OK |
| viscosity_index | 1.8-3.5 | 1.85 | OK |
| water_absorption | 1.4-2.2 | 1.84 | OK |

But simulated volume stayed around +66%, while the bread target is +90%.

Interpretation: the current fermentation/volume model may be too conservative for bread or the sampled ingredient pool cannot reach the target. This should be tested experimentally with high-hydration, psyllium/HPMC bread formulations.

### 3. Sweet Leavened Products Need Better Richness/Sweetness Modeling

Top candidates are functional, but flavor vectors remain too neutral and not rich/sweet enough:

| Flavor Dimension | Target | Median Top-10 | Delta |
|---|---:|---:|---:|
| sweet | 0.42 | 0.19 | -0.23 |
| rich | 0.38 | 0.15 | -0.23 |
| cereal | 0.42 | 0.26 | -0.16 |

Interpretation: this is expected because the model only sees flour/starch ingredients. Real sweet leavened products depend heavily on sugar, eggs, butter/oil, milk, and aroma compounds, none of which are modeled yet.

Action: do not rely on the current flavor score for sweet leavened products until non-flour ingredients are represented.

### 4. Frolla And Biscotti Are Strong Use Cases

Frolla top candidates:

| Metric | Target Range | Median Top-10 | Status |
|---|---:|---:|---|
| fat_pct | 8-30 | 16.0 | OK |
| hydrocolloid_pct | 0-1% | 0.48% | OK |
| starch_pct | 45-75 | 62.3 | OK |
| viscosity_index | 0.5-1.2 | 1.12 | OK |
| water_absorption | 0.7-1.3 | 1.12 | OK |

Top frolla candidate:

```text
Score: 0.928
Volume: +7.8%
Core: 82.0C
Crust: 159.2C
Blend: white rice 37.1%, almond 32.1%, corn starch 26.1%, oat 2.9%, minor remainder
```

Biscotti top candidates also look coherent, with almond around 30-40%, rice/corn starch base, low hydrocolloid, and low/moderate volume.

Interpretation: low-volume applications are currently easier for the model because functional targets map directly to ingredient properties and do not depend strongly on complex gas retention dynamics.

### 5. Pasta Fresca Is Not Valid Yet

Pasta fresca was the weakest process result:

```text
Top process score: 0.548
Core: 38.7C
Crust: 85.8C
```

This is expected because the current process simulator is a baking model, not a boiling/cooking-loss pasta model.

Interpretation: pasta should not use `BakingSimulator` as the main validation process. It needs dedicated metrics:

- cooking loss
- firmness
- stickiness
- sheet cohesion
- water uptake

Action: mark pasta process optimization as placeholder until a pasta-specific simulator is implemented.

## Model Validity Assessment

| Area | Current Validity | Notes |
|---|---|---|
| Pizza blend functional score | Medium-high | Ranges and candidates look plausible. |
| Pizza process score | Medium | Needs validation of crust/core vs real pizza baking. |
| Bread blend functional score | Medium | Ranges plausible, but volume target may be too high for current model. |
| Bread process score | Medium-low | Needs measured specific volume. |
| Frolla/Biscotti | High for pre-screening | Candidates align well with expected low-volume, high-fat/starch behavior. |
| Pasta fresca | Low | Requires pasta-specific simulator. |
| Flavor model | Low-medium | Useful for filtering strong off-flavor risks, not calibrated. |

## Recommended Lab Trials

Start with the cases where the model is most internally coherent.

### Trial Group A: Pizza

Test 3 candidates:

- High sorghum/potato starch candidate from top pizza result.
- More rice/tapioca balanced candidate.
- Higher psyllium candidate near the upper pizza hydrocolloid range.

Measure:

- dough handling
- spreadability/extensibility
- baked height/edge expansion
- crumb gumminess
- crust color
- sensory cereal/earthy/bitter notes

### Trial Group B: Frolla/Biscotti

Test 2-3 candidates using almond/rice/corn starch blends.

Measure:

- spread ratio
- snap/fracturability
- hardness
- perceived richness/nuttiness
- shape hold

### Trial Group C: Bread

Test 2 candidates only after adding or emphasizing HPMC/psyllium variants.

Measure:

- specific volume ml/g
- crumb hardness after 2h and 24h
- gumminess
- moisture retention

## Recommended Model Changes

1. Add a product-specific process model for pasta before treating pasta results as meaningful.
2. Add non-flour ingredients for sweet leavened products: sugar, oil/butter, egg/milk proxies.
3. Add baking aroma correction to flavor model: `toasted` and `cereal` should increase with crust temperature/time.
4. Add experimental calibration fields: `n_trials`, `measured_error`, `calibration_status` per profile.
5. Introduce measured specific volume for bread/pizza rather than relying only on fermentation volume increase.

## Conclusion

The massive benchmark suggests Glutenix is already useful as a pre-screening system for pizza, frolla, and biscotti. Bread is promising but needs real specific-volume calibration. Pasta is not ready because the process model does not represent boiling/cooking behavior.

The most practical next step is to run a small lab validation on pizza and frolla/biscotti candidates, because those applications currently show the strongest agreement between process score, functional blend score, and flavor proxy.
