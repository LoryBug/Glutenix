# Literature-First Validation Roadmap

Date: 2026-06-19

Glutenix cannot be treated as experimentally validated until real lab or kitchen trials are available. Until then, the most credible path is to make it a literature-first simulation system: every prediction should be connected to evidence coverage, known assumptions, and explicit uncertainty.

The goal is not to make the simulator look more certain than it is. The goal is to make it useful, transparent, and progressively more valid inside well-defined domains.

## Target State

Glutenix should evolve from:

```text
heuristic simulator that suggests gluten-free blends
```

to:

```text
evidence-aware formulation assistant that simulates, validates against literature,
detects extrapolation, reports confidence, and prioritizes meaningful tests
```

The system should help answer these questions before any physical test is run:

- Is this formulation physically plausible for the selected application?
- Is this candidate inside literature-covered ingredient and process ranges?
- Which model outputs are calibrated, heuristic, or extrapolated?
- Which inputs most strongly affect the result?
- Which recipe is worth testing first, and why?

## Validation Principles

- Literature data is evidence, not ground truth for every kitchen or lab context.
- Linear corrections are diagnostic unless validated on independent sources.
- Heuristic models must stay explicitly labeled as heuristic.
- Predictions should include confidence and risk flags, not only scores.
- A model is valid only inside the ingredient, process, and metric space where it has evidence.
- More coefficients are less useful than broader cross-paper validation.

## Phase 1: Evidence Map

Create and maintain a project-wide evidence map that tracks what Glutenix can support today.

The evidence map should summarize:

- Applications covered by literature.
- Metrics available per application.
- Ingredient families represented in the data.
- Process families represented in the data.
- Current simulator confidence by domain.
- Gaps and next literature targets.

Expected output:

- `docs/evidence-map.md`
- A compact table for each application.
- A priority list for the next paper extractions.

Why this matters:

- It prevents random literature accumulation.
- It makes extrapolation visible.
- It guides which simulator should be improved next.

## Phase 2: Standardized Literature Datasets

The existing pasta dataset is a good pattern. The same structure should be extended to other domains.

Planned datasets:

```text
data/literature/pasta_cooking.jsonl
data/literature/bread_baking.jsonl
data/literature/pizza_baking.jsonl
data/literature/dough_rheology.jsonl
data/literature/shortcrust_baking.jsonl
```

Every literature record should include:

```json
{
  "id": "source_year_sample",
  "application": "Pane",
  "source": {
    "title": "...",
    "doi": "...",
    "pmcid": "...",
    "url": "...",
    "table": "..."
  },
  "literature_formula": {},
  "mapped_formula": {},
  "mapping_notes": "...",
  "process": {},
  "measured": {},
  "confidence": "high"
}
```

Required validation rules:

- Formula values must be positive finite numbers.
- `mapped_formula` must normalize over dry/solid ingredients when water is a process variable.
- Measured metrics must keep the original published scale unless explicitly converted.
- Converted metrics must preserve the original value in a separate field.
- Each record must include source metadata sufficient for traceability.

## Phase 3: Bread Literature Validation

Bread should be the next major domain after pasta because gluten-free bread is widely studied and directly exercises the baking and fermentation simulators.

Metrics to extract:

- Specific volume.
- Loaf height.
- Baking loss.
- Crumb moisture.
- Water activity.
- Crumb hardness or firmness.
- Staling over 24, 48, and 72 hours.
- Porosity or cell structure metrics.
- Sensory acceptability where numeric tables exist.

Ingredient/process families to prioritize:

- Rice/corn starch bread systems.
- HPMC, xanthan, psyllium, guar, and mixed hydrocolloids.
- Protein enrichment such as egg, soy, pea, whey, or legume flours.
- Fiber enrichment such as psyllium, oat fiber, inulin, or resistant starch.
- Sourdough or yeast fermentation where process data is clear.

Expected implementation:

- `data/literature/bread_baking.jsonl`
- `glutenix/calibration/bread.py` or shared generalized calibration helpers.
- `GET /calibration/bread-baking`
- `docs/bread-baking-calibration-report.md`

## Phase 4: Domain-Specific Quality Simulators

The current engine has shared blend, fermentation, baking, cooking, and flavor components. To become more valid, application-specific quality layers should be added on top of shared physics signals.

Planned simulators:

```text
BreadQualitySimulator
PizzaQualitySimulator
PastaCookingSimulator
ShortcrustQualitySimulator
SweetLeavenedQualitySimulator
```

Bread outputs should include:

- Volume score.
- Crumb firmness proxy.
- Moisture retention proxy.
- Gumminess risk.
- Collapse risk.
- Staling risk.

Pizza outputs should include:

- Center-bake risk.
- Crust crispness proxy.
- Chewiness proxy.
- Gumminess risk.
- Extensibility risk.
- Browning/process fit.

Shortcrust/biscuit outputs should include:

- Spread risk.
- Friability proxy.
- Hardness risk.
- Moisture retention.
- Fat/starch balance.

These layers should use existing simulator signals where possible and avoid adding complex new coefficients unless backed by literature or clear model structure.

## Phase 5: Calibration Reports Per Domain

Every domain-specific simulator needs a report similar to the current pasta cooking report.

Planned endpoints:

```text
GET /calibration/pasta-cooking
GET /calibration/bread-baking
GET /calibration/pizza-baking
GET /calibration/coverage
```

Each calibration report should include:

- Number of records.
- Number of sources.
- Main metric and auxiliary metrics.
- MAE, RMSE, and bias.
- Grouped errors by source.
- Grouped errors by process family.
- Grouped errors by important formulation factors.
- Outliers.
- Ingredient and process coverage.
- Diagnostic correction parameters, if meaningful.
- Explicit statement of whether the correction is diagnostic or production-ready.

## Phase 6: Better Confidence And Coverage

The current `model_confidence` output is a first step. It should become more structured and evidence-driven.

Target output shape:

```json
{
  "score": 0.72,
  "level": "medium",
  "coverage": {
    "ingredient_space": 0.80,
    "process_space": 0.60,
    "application_evidence": 0.70,
    "metric_validation": 0.50
  },
  "nearest_sources": ["..."],
  "risk_flags": ["..."],
  "evidence_sources": ["..."]
}
```

Coverage dimensions:

- Ingredient coverage: whether the ingredient family and proportions are represented in literature.
- Process coverage: whether temperature, time, hydration, extrusion, proofing, or baking settings are represented.
- Application evidence: whether the product category has direct measured records.
- Metric validation: whether the reported output has measured validation data.

## Phase 7: Out-Of-Distribution Detection

Out-of-distribution detection is essential for a credible simulator.

Examples:

- Literature covers HPMC at 1-4%, but a candidate uses 8%.
- Literature covers hydration at 80-110%, but a candidate uses 150%.
- Literature covers rice/corn bread, but a candidate uses mostly almond flour.
- Literature covers fresh calcium-alginate pasta, but the candidate is dried extruded pasta without extrusion metadata.

Expected output:

```json
{
  "ood_score": 0.82,
  "ood_level": "high",
  "reasons": [
    "hydrocolloid_pct above literature range",
    "baking_temp outside covered range"
  ]
}
```

Implementation path:

- Derive coverage ranges from literature records.
- Compare candidate blend/process values to known ranges.
- Add OOD details to `model_confidence`.
- Expose coverage at `/calibration/coverage`.

## Phase 8: Sensitivity Analysis

Without real experiments, sensitivity analysis is one of the best ways to understand robustness.

New endpoint:

```text
POST /simulate/sensitivity
```

Expected output:

```json
{
  "stability_score": 0.68,
  "most_sensitive_inputs": [
    "water_absorption",
    "hydrocolloid_pct",
    "baking_duration_min"
  ],
  "risk_flags": [
    "Small hydration changes strongly affect predicted quality"
  ]
}
```

Useful approaches:

- Local one-at-a-time perturbation.
- Process sweep variance.
- Blend proportion perturbation within bounds.
- Sobol-style analysis later if needed.

## Phase 9: Model Cards

Every simulator should have a model card.

Planned docs:

```text
docs/model-card-pasta-cooking.md
docs/model-card-bread-baking.md
docs/model-card-pizza-baking.md
docs/model-card-flavor.md
```

Each model card should include:

- What the model predicts.
- Inputs and outputs.
- Evidence sources.
- Covered ingredient/process ranges.
- Metrics validated against literature.
- Known weaknesses.
- Heuristic assumptions.
- Out-of-domain examples.
- Current confidence level.

## Phase 10: Validation Dashboard

Create a single document or endpoint summarizing the status of all domains.

Example table:

| Domain | Papers | Records | Main Metrics | Confidence | Status |
|---|---:|---:|---|---|---|
| Pasta cooking | 5 | 42 | Cooking loss, water uptake, swelling | Medium-high | Literature calibrated |
| Bread baking | 3 | 15 | Specific volume, limited firmness | Medium-low | Early diagnostic validation |
| Pizza baking | 0 | 0 | Texture, crust, bake fit | Low | Heuristic |
| Flavor | 0 | 0 | Sensory profile proxy | Low | Heuristic |

This dashboard should be updated whenever new literature data is added.

## Operational Priority

Recommended sequence:

1. Build the evidence map.
2. Add the first bread baking literature dataset.
3. Add bread calibration comparison and report.
4. Add coverage/OOD calculation from literature ranges.
5. Create model cards for pasta and bread.
6. Add pizza literature dataset.
7. Add sensitivity analysis.
8. Expand frontend only after confidence and evidence data are useful enough to display.

## Definition Of A More Valid System

Glutenix becomes meaningfully more valid when it can do all of the following:

- Compare simulator output against multiple independent papers per domain.
- Report errors by source and process family.
- Warn when a candidate is outside literature coverage.
- Separate calibrated metrics from heuristic proxies.
- Explain why each candidate is suggested.
- Show which inputs drive prediction instability.
- Keep every assumption traceable to source data, model code, or documented heuristic reasoning.

That is the path from an interesting simulator to a credible formulation assistant.
