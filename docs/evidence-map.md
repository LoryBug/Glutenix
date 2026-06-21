# Glutenix Evidence Map

Date: 2026-06-20

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

<!-- generated-start: evidence-domain-coverage -->
| Domain | Current Evidence | Records | Sources | Main Metrics | Current Confidence | Next Priority |
|---|---:|---:|---:|---|---|---|
| Pasta cooking | `calibrated` | 42 | 5 | Cooking loss, water uptake, swelling | Medium-high | Add more dried/fresh pasta systems and texture data |
| Bread baking | `literature-informed` | 65 | 10 | Specific volume, crumb hardness, porosity | Medium-low | Add more hydrocolloid/protein/fiber bread records |
| Pizza baking | `heuristic` | 0 | 0 | Process fit, crust/core targets, blend targets | Low | Add pizza or flatbread dataset after bread |
| Sweet leavened doughs | `heuristic` | 0 | 0 | Volume/process/blend targets | Low | Extract enriched dough literature later |
| Shortcrust/frolla | `heuristic` | 0 | 0 | Low-volume process fit, fat/starch balance | Low | Add biscuit/shortcrust texture papers later |
| Biscuits/cookies | `heuristic` | 0 | 0 | Low expansion, crispness proxies | Low | Add biscuit/cookie texture papers later |
| Flavor | `heuristic` | 0 | 0 | Flavor profile proxy | Low | Needs sensory panel literature or internal tests |
| Nutrition | `literature-informed` | Seed data | Mixed source values | Macro estimates | Medium for approximate labels | Needs source-level ingredient provenance |
<!-- generated-end: evidence-domain-coverage -->

## Simulator Coverage

| Module | Status | Evidence Basis | Main Gaps |
|---|---|---|---|
| `BlendCalculator` | `literature-informed` | Ingredient composition and approximate functional properties | Ingredient provenance and variance ranges are not fully tracked |
| `FermentationSimulator` | `heuristic` | Mechanistic proxy for gas/volume behavior | No direct validation against gluten-free dough fermentation data |
| `BakingSimulator` | `literature-informed` | Heat-transfer and gelatinization-inspired proxy plus first bread comparison dataset | Needs broader bread/pizza baking validation |
| `BreadQualitySimulator` | `literature-informed` | 65 bread records from 10 papers, covering specific volume, crumb hardness, and porosity | Early diagnostic model; hardness and porosity need more sources |
| `PastaCookingSimulator` | `calibrated` | 42 records from 5 pasta papers | Limited texture validation and source balance |
| `FlavorModel` | `heuristic` | Literature-informed sensory proxy | No measured sensory panel calibration |
| `ApplicationSuggest` | `heuristic + confidence` | Target profiles, process scores, flavor score, pasta calibration where available | Needs domain calibration beyond pasta |
| `ModelConfidence` | `initial + OOD` | Blend target range fit, score bands, pasta calibration score, literature-derived coverage ranges plus bread mechanism/calibration reliability | Needs richer coverage distances and source-specific uncertainty |

## Application Evidence Details

### Pasta Fresca

Current status: `calibrated` for selected pasta cooking metrics.

Structured records:

- 42 total records.
- 5 peer-reviewed sources.
- 30 fresh calcium-alginate amaranth pasta records.
- 10 dried extruded rice pasta records.
- 2 instant extrusion-cooked rice/rice-buckwheat pasta records.

Current sources:

- `lux_2023`: calcium-alginate amaranth pasta.
- `liu_2026`: extruded rice pasta with KGM and curdlan.
- `detchewa_2016`: extruded rice spaghetti with soy protein isolate.
- `bouasla_2019`: instant extrusion-cooked rice-buckwheat pasta.
- `bouasla_2021`: instant extrusion-cooked rice pasta.

Full citation metadata is centralized in `data/literature/sources.json` and rendered in `docs/generated/bibliography.md`.

Covered process families:

- `fresh_calcium_gel`
- `dried_extruded`
- `instant_extruded`
- `generic_fresh` only as low-confidence heuristic mode

Covered ingredients and mechanisms:

- Amaranth flour.
- Sodium alginate.
- Calcium lactate bath.
- High-amylose rice flour.
- White rice flour.
- Sweet/waxy rice flour.
- Buckwheat flour.
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
- Chickpea, lentil, pea, and quinoa pasta systems.
- Texture metrics such as firmness, hardness, adhesiveness, chewiness, and tensile strength.
- Sensory scores.
- Independent train/test calibration split.

Next literature targets:

- Dried corn/rice pasta with hydrocolloids and clear cooking loss tables.
- Legume-enriched gluten-free pasta with cooking and texture metrics.
- Fresh gluten-free pasta papers with formulation, hydration, and cooking process details.
- Papers with table values for hardness, adhesiveness, chewiness, and optimal cooking time.

### Pane

Current status: `literature-informed` with early diagnostic comparison.

Current model support:

- Application target profile exists.
- Process sweep can optimize fermentation and baking settings.
- Blend score uses water absorption, viscosity, hydrocolloid fraction, fiber, and protein ranges.
- Baking simulator estimates core/crust temperature and gelatinization-inspired heat behavior.
- Bread quality simulator estimates specific volume, crumb hardness proxy, porosity, moisture retention, staling risk, and structure index.

Structured records:

- 65 total records.
- 10 peer-reviewed sources.
- 9 proso millet cultivar bread records.
- 4 commercial gluten-free bread mix additive-removal records.
- 2 rice/chickpea/whey protein bread records (Loncaric 2026).
- 3 chickpea-protein-enriched breads with raw/roasted/dehulled varieties (Kahraman 2022).
- 6 rice-flour and maize-starch HPMC/psyllium/xanthan breads (Belorio 2020).
- 6 explicit HPMC/xanthan/guar hydrocolloid-combination bread records (Parsamajd 2025).
- 6 pea-protein-enriched breads at 0-25% substitution (Wojcik 2021).
- 9 tapioca starch/red lentil flour mixture design bread records (Bianchi 2026).
- 15 quinoa flour + HPMC + TG CCD design bread records (Ghodosipoor 2025).
- 5 quinoa/rice/potato starch hydrocolloid bread records (Di Renzo 2024).

Current sources:

- `singh_2026`: proso millet cultivar gluten-free breads.
- `torres_perez_2026`: additive-removal clean-label gluten-free bread.
- `loncaric_2026`: rice/whey and rice/chickpea gluten-free bread staling.
- `parsamajd_2025`: HPMC/xanthan/guar hydrocolloid-combination gluten-free breads.
- `belorio_gomez_2020`: hydration effects in rice/maize HPMC/psyllium/xanthan breads.
- `wojcik_2021`: pea-protein-enriched buckwheat/flaxseed gluten-free bread.
- `kahraman_2022`: raw/roasted/dehulled chickpea flour in rice-based gluten-free bread.
- `bianchi_2026`: tapioca starch/red lentil flour mixture design gluten-free bread with guar gum.
- `ghodosipoor_2025`: quinoa flour + HPMC + microbial transglutaminase CCD gluten-free bread optimization.
- `di_renzo_2024`: quinoa/rice/potato gluten-free bread with HPMC, xanthan, sodium alginate, and kappa carrageenan.

Full citation metadata is centralized in `data/literature/sources.json` and rendered in `docs/generated/bibliography.md`.

Current limitations:

- Specific volume is the broadest metric with 59 structured records.
- Crumb hardness has 40 structured records across six sources.
- Porosity has 11 structured records across three sources (Loncaric 2026, Parsamajd 2025, Kahraman 2022), but values may depend strongly on image-analysis method.
- Bread coverage confidence now separates range coverage from mechanism/calibration reliability; TG/enzyme and sparse quinoa cases are downgraded even when numeric ranges pass.
- Commercial bread mix records are aggregate-mapped because internal proportions are not disclosed.
- Millet cultivar records share a generic `Millet flour` mapping, so cultivar-specific starch functionality is simplified.
- No independent train/test split is meaningful yet.

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

Implemented first action:

- Build `data/literature/bread_baking.jsonl`.
- Add a diagnostic `GET /calibration/bread-baking` endpoint.
- Add `GET /calibration/coverage` for literature-derived range/OOD diagnostics.

Recommended next action:

- Add 2-3 more bread papers focused on HPMC/xanthan/psyllium levels with specific volume and hardness tables.
- Add source-specific ingredient/property notes for millet cultivars if cultivar composition data is extractable.

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
| Specific volume | Not applicable | Structured | Missing | Missing | Usually not primary |
| Core/crust process fit | Not primary | Heuristic | Heuristic | Heuristic | Heuristic |
| Firmness/hardness | Modeled proxy, not validated | Limited structured | Missing | Missing | Missing |
| Stickiness/gumminess | Modeled proxy, not validated | Missing | Missing | Missing | Missing |
| Porosity/cell structure | Not primary | Limited structured | Missing | Missing | Missing |
| Moisture retention | Not validated | Auxiliary structured moisture values only | Missing | Missing | Missing |
| Sensory score | Not validated | Missing | Missing | Missing | Missing |

## Ingredient Coverage Matrix

| Ingredient Family | Pasta | Bread | Pizza | Notes |
|---|---|---|---|---|
| Rice flour/starch | Medium | Heuristic | Heuristic | Pasta has high-amylose, waxy, and white rice records |
| Corn starch/flour | Low | Structured in bread | Heuristic | Needs more bread/pizza literature records |
| Tapioca starch | Low | Structured in bread | Heuristic | Covered in one hydrocolloid bread source |
| Potato starch | Low | Heuristic | Heuristic | Seeded but not validated by literature datasets |
| Amaranth flour | Medium | Heuristic | Heuristic | Covered in calcium-alginate pasta only |
| Buckwheat/quinoa/teff/millet | Low-medium | Limited structured | Heuristic | Buckwheat appears in one pasta record; millet and quinoa appear in bread records, but cultivar/source coverage is limited |
| HPMC | Low | Limited structured | Heuristic | Covered in one hydrocolloid bread source |
| Xanthan/guar | Low | Limited structured | Heuristic | Covered in one hydrocolloid bread source plus xanthan proxy records |
| Psyllium | Low | Heuristic | Heuristic | High priority for bread/pizza literature |
| Alginate | Medium | Low | Low | Covered for fresh calcium pasta |
| KGM/curdlan | Medium | Low | Low | Covered for dried rice pasta |
| Soy protein isolate | Medium | Low | Low | Covered for dried rice pasta |

## Process Coverage Matrix

| Process Family | Current Evidence | Coverage Notes |
|---|---|---|
| Fresh calcium-gel pasta | Medium-high | 30 records from Lux 2023 |
| Dried extruded rice pasta | Medium | 10 records from Liu 2026 and Detchewa 2016 |
| Instant extrusion-cooked rice pasta | Medium-low | 2 records from Bouasla & Wojtowicz 2019/2021 |
| Generic fresh pasta | Low | Heuristic fallback only |
| Yeast-fermented bread | Medium-low | 65 records from 10 sources, specific volume and crumb hardness from hydrocolloid and protein-enriched families |
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

1. Add 2-3 more bread papers with explicit hydrocolloid-level variation.
2. Add `docs/bread-baking-calibration-report.md`.
3. Derive ingredient/process coverage ranges from literature records.
4. Feed those ranges into `model_confidence` as OOD warnings.
5. Add pizza/flatbread literature after bread coverage is broader.

## Current Summary

Glutenix is currently strongest for pasta cooking and now has an initial, diagnostic bread validation dataset.

The most important next move is not more frontend work and not more coefficient tuning. The most important next move is broader structured bread literature extraction, especially papers that isolate HPMC, xanthan, psyllium, protein, and fiber effects with numeric volume and texture tables.
