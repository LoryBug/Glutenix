# Glutenix Evidence Map

Date: 2026-06-19

This document tracks what Glutenix can currently support with literature evidence, what is still heuristic, and which literature should be added next.

The evidence map is intentionally conservative. A model can be useful before it is fully validated, but Glutenix should always state whether a prediction is calibrated, literature-informed, heuristic, or extrapolated.

## Evidence Levels

| Level | Meaning |
|---|---|
| `calibrated` | Compared against structured measured records from multiple literature sources. |
| `literature-informed` | Based on literature ranges or mechanisms, but not yet quantitatively validated in Glutenix. |
| `heuristic` | Based on plausible food-science logic or internal scoring, without direct validation data. |
| `extrapolated` | Outside current ingredient, process, or metric coverage. |

## Current Domain Coverage

| Domain | Current Evidence | Records | Sources | Main Metrics | Current Confidence | Next Priority |
|---|---:|---:|---:|---|---|---|
| Pasta cooking | `calibrated` | 40 | 3 | Cooking loss, water uptake, swelling | Medium-high | Add more dried/fresh pasta systems and texture data |
| Bread baking | `heuristic` | 0 | 0 | Volume proxy, bake fit, blend targets | Low | Add bread baking dataset |
| Pizza baking | `heuristic` | 0 | 0 | Process fit, crust/core targets, blend targets | Low | Add pizza or flatbread dataset after bread |
| Sweet leavened doughs | `heuristic` | 0 | 0 | Volume/process/blend targets | Low | Extract enriched dough literature later |
| Shortcrust/frolla | `heuristic` | 0 | 0 | Low-volume process fit, fat/starch balance | Low | Add biscuit/shortcrust texture papers later |
| Biscuits/cookies | `heuristic` | 0 | 0 | Low expansion, crispness proxies | Low | Add biscuit/cookie texture papers later |
| Flavor | `heuristic` | 0 | 0 | Flavor profile proxy | Low | Needs sensory panel literature or internal tests |
| Nutrition | `literature-informed` | Seed data | Mixed source values | Macro estimates | Medium for approximate labels | Needs source-level ingredient provenance |

## Simulator Coverage

| Module | Status | Evidence Basis | Main Gaps |
|---|---|---|---|
| `BlendCalculator` | `literature-informed` | Ingredient composition and approximate functional properties | Ingredient provenance and variance ranges are not fully tracked |
| `FermentationSimulator` | `heuristic` | Mechanistic proxy for gas/volume behavior | No direct validation against gluten-free dough fermentation data |
| `BakingSimulator` | `heuristic` | Heat-transfer and gelatinization-inspired proxy | No measured bread/pizza baking dataset yet |
| `PastaCookingSimulator` | `calibrated` | 40 records from 3 pasta papers | Limited texture validation and only 3 sources |
| `FlavorModel` | `heuristic` | Literature-informed sensory proxy | No measured sensory panel calibration |
| `ApplicationSuggest` | `heuristic + confidence` | Target profiles, process scores, flavor score, pasta calibration where available | Needs domain calibration beyond pasta |
| `ModelConfidence` | `initial` | Blend target range fit, score bands, pasta calibration score | Needs literature-derived OOD distances |

## Application Evidence Details

### Pasta Fresca

Current status: `calibrated` for selected pasta cooking metrics.

Structured records:

- 40 total records.
- 3 peer-reviewed sources.
- 30 fresh calcium-alginate amaranth pasta records.
- 10 dried extruded rice pasta records.

Current sources:

- Lux et al. 2023, DOI `10.1002/fsn3.3301`, calcium-alginate amaranth pasta.
- Liu et al. 2026, DOI `10.1016/j.fochx.2025.103403`, extruded rice pasta with KGM and curdlan.
- Detchewa et al. 2016, DOI `10.1007/s13197-016-2323-8`, extruded rice spaghetti with soy protein isolate.

Covered process families:

- `fresh_calcium_gel`
- `dried_extruded`
- `generic_fresh` only as low-confidence heuristic mode

Covered ingredients and mechanisms:

- Amaranth flour.
- Sodium alginate.
- Calcium lactate bath.
- High-amylose rice flour.
- Sweet/waxy rice flour.
- Konjac glucomannan.
- Curdlan.
- Soy protein isolate.
- Pregelatinization and heating terms.
- Syneresis/water release in high-water alginate systems.
- Starch leaching and cooking loss.

Validated metrics:

- `cooking_loss_pct`
- `water_absorption_pct` for records where scale is compatible
- `swelling_index` for Lux records

Tracked but not summarized as equivalent:

- `water_adsorption_index_pct` from Detchewa, because the scale differs from current water uptake targets.

Known gaps:

- Fresh egg pasta systems.
- Corn/rice commercial pasta systems without alginate.
- Chickpea, lentil, pea, quinoa, buckwheat pasta systems.
- Texture metrics such as firmness, hardness, adhesiveness, chewiness, and tensile strength.
- Sensory scores.
- Independent train/test calibration split.

Next literature targets:

- Dried corn/rice pasta with hydrocolloids and clear cooking loss tables.
- Legume-enriched gluten-free pasta with cooking and texture metrics.
- Fresh gluten-free pasta papers with formulation, hydration, and cooking process details.
- Papers with table values for hardness, adhesiveness, chewiness, and optimal cooking time.

### Pane

Current status: `heuristic`.

Current model support:

- Application target profile exists.
- Process sweep can optimize fermentation and baking settings.
- Blend score uses water absorption, viscosity, hydrocolloid fraction, fiber, and protein ranges.
- Baking simulator estimates core/crust temperature and gelatinization-inspired heat behavior.

Current missing evidence:

- No structured `bread_baking.jsonl` dataset.
- No direct comparison to specific volume.
- No direct comparison to crumb hardness/firmness.
- No direct comparison to moisture retention or staling.
- No direct comparison by hydrocolloid type.

Priority metrics to extract:

- Specific volume.
- Loaf height.
- Baking loss.
- Crumb moisture.
- Crumb hardness or firmness.
- Porosity/cell structure.
- Staling after 24, 48, and 72 hours.
- Sensory acceptability if numeric tables are available.

Priority ingredient/process families:

- Rice/corn starch base systems.
- HPMC.
- Xanthan gum.
- Psyllium.
- Guar gum.
- Protein-enriched bread.
- Fiber-enriched bread.
- Sourdough or yeast fermentation with clear process data.

Recommended next action:

- Extract 2-3 bread papers with table-based numeric metrics and complete formulas.
- Build `data/literature/bread_baking.jsonl`.
- Add a diagnostic `GET /calibration/bread-baking` endpoint.

### Pizza

Current status: `heuristic`.

Current model support:

- Application target profile exists.
- Process sweep can optimize fermentation and baking settings.
- Blend score uses water absorption, viscosity, hydrocolloid fraction, fiber, and fat ranges.
- Baking simulator can estimate core/crust process fit.

Current missing evidence:

- No structured pizza dataset.
- No direct comparison to crust texture.
- No direct comparison to dough extensibility or handling.
- No direct comparison to sensory score.
- No direct comparison to baking loss.

Priority metrics to extract:

- Dough extensibility.
- Dough firmness or rheology metrics.
- Crust hardness.
- Crumb/cell porosity.
- Baking loss.
- Specific volume or height where available.
- Sensory acceptability.

Priority ingredient/process families:

- Rice/corn/tapioca pizza bases.
- Psyllium and HPMC pizza systems.
- High hydration gluten-free pizza dough.
- Sourdough gluten-free pizza.
- Protein or fiber enrichment.

Recommended next action:

- Add after bread, unless a strong pizza paper with complete tables is found first.

### Lievitati Dolci

Current status: `heuristic`.

Current model support:

- Application target profile exists.
- Higher volume target than bread/pizza.
- Gentle crust target.
- Blend ranges include fat and fiber.
- Flavor target allows sweetness and richness.

Current missing evidence:

- No structured enriched gluten-free dough dataset.
- No comparison to volume, softness, staling, or sensory scores.

Priority metrics to extract:

- Specific volume.
- Firmness/softness.
- Moisture.
- Staling.
- Sensory acceptability.

Priority ingredient/process families:

- Gluten-free brioche-like dough.
- Panettone-like or sweet bread systems if numeric data exists.
- Egg/fat/sugar-enriched formulations.
- Hydrocolloid and emulsifier studies.

Recommended next action:

- Defer until bread calibration is established.

### Frolla, Biscotti, And Shortcrust Systems

Current status: `heuristic`.

Current model support:

- Application target profiles exist for frolla and biscuits.
- Low-volume process logic exists.
- Blend ranges penalize excessive hydrocolloid and account for fat/starch balance.

Current missing evidence:

- No structured shortcrust or biscuit dataset.
- No direct comparison to hardness, spread, snap, friability, or sensory score.

Priority metrics to extract:

- Spread ratio.
- Hardness.
- Fracturability.
- Moisture.
- Color/browning.
- Sensory acceptability.

Priority ingredient/process families:

- Rice/corn/tapioca biscuit bases.
- Almond, buckwheat, oat, or fiber-enriched biscuits.
- Hydrocolloid-free or low-hydrocolloid shortcrust systems.

Recommended next action:

- Defer until bread and pizza have at least minimal structured validation.

## Metric Coverage Matrix

| Metric | Pasta | Bread | Pizza | Sweet Dough | Shortcrust/Biscuit |
|---|---|---|---|---|---|
| Cooking loss | Structured | Not applicable | Not applicable | Not applicable | Not applicable |
| Water uptake | Structured, scale-dependent | Missing | Missing | Missing | Missing |
| Swelling | Structured for Lux | Missing | Missing | Missing | Missing |
| Specific volume | Not applicable | Missing | Missing | Missing | Usually not primary |
| Core/crust process fit | Not primary | Heuristic | Heuristic | Heuristic | Heuristic |
| Firmness/hardness | Modeled proxy, not validated | Missing | Missing | Missing | Missing |
| Stickiness/gumminess | Modeled proxy, not validated | Missing | Missing | Missing | Missing |
| Moisture retention | Not validated | Missing | Missing | Missing | Missing |
| Sensory score | Not validated | Missing | Missing | Missing | Missing |

## Ingredient Coverage Matrix

| Ingredient Family | Pasta | Bread | Pizza | Notes |
|---|---|---|---|---|
| Rice flour/starch | Medium | Heuristic | Heuristic | Pasta has high-amylose and waxy rice records |
| Corn starch/flour | Low | Heuristic | Heuristic | Needs bread/pizza literature records |
| Tapioca starch | Low | Heuristic | Heuristic | Seeded but not validated by literature datasets |
| Potato starch | Low | Heuristic | Heuristic | Seeded but not validated by literature datasets |
| Amaranth flour | Medium | Heuristic | Heuristic | Covered in calcium-alginate pasta only |
| Buckwheat/quinoa/teff/millet | Low | Heuristic | Heuristic | Flavor and blend heuristics only |
| HPMC | Low | Heuristic | Heuristic | High priority for bread literature |
| Xanthan/guar | Low | Heuristic | Heuristic | High priority for bread literature |
| Psyllium | Low | Heuristic | Heuristic | High priority for bread/pizza literature |
| Alginate | Medium | Low | Low | Covered for fresh calcium pasta |
| KGM/curdlan | Medium | Low | Low | Covered for dried rice pasta |
| Soy protein isolate | Medium | Low | Low | Covered for dried rice pasta |

## Process Coverage Matrix

| Process Family | Current Evidence | Coverage Notes |
|---|---|---|
| Fresh calcium-gel pasta | Medium-high | 30 records from Lux 2023 |
| Dried extruded rice pasta | Medium | 10 records from Liu 2026 and Detchewa 2016 |
| Generic fresh pasta | Low | Heuristic fallback only |
| Yeast-fermented bread | Low | Simulated but not literature-calibrated |
| High-temperature pizza baking | Low | Simulated but not literature-calibrated |
| Sweet enriched leavened dough | Low | Simulated but not literature-calibrated |
| Shortcrust/biscuit baking | Low | Simulated but not literature-calibrated |

## Immediate Literature Priorities

Priority 1: Gluten-free bread with hydrocolloids.

Desired properties:

- Complete formula table.
- Clear hydration and baking process.
- Specific volume table.
- Crumb hardness/firmness table.
- Moisture or staling data if available.

Priority 2: Gluten-free bread with protein or fiber enrichment.

Desired properties:

- Formula table with protein/fiber substitutions.
- Volume and texture metrics.
- Sensory score if numeric.

Priority 3: Gluten-free pizza or flatbread.

Desired properties:

- Dough/process table.
- Texture metrics.
- Baking loss or physical dimensions.
- Sensory score if numeric.

Priority 4: More pasta texture validation.

Desired properties:

- Cooking loss.
- Firmness/hardness.
- Stickiness/adhesiveness.
- Optimal cooking time.
- Ingredient and process clarity.

## Next Implementation Tasks

1. Add `data/literature/bread_baking.jsonl` with 2-3 high-quality papers.
2. Generalize literature loading helpers so bread and pasta share validation logic where possible.
3. Add bread calibration comparison for specific volume and firmness.
4. Add `GET /calibration/bread-baking`.
5. Add `docs/bread-baking-calibration-report.md`.
6. Derive ingredient/process coverage ranges from literature records.
7. Feed those ranges into `model_confidence` as OOD warnings.

## Current Summary

Glutenix is currently strongest for pasta cooking and weakest for baked-product validation.

The most important next move is not more frontend work and not more coefficient tuning. The most important next move is structured bread literature extraction, because it validates the core baking/fermentation path and makes the project broader than pasta.
