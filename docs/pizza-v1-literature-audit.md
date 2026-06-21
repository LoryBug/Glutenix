# Pizza V1 Literature Audit

Date: 2026-06-21

This audit defines the evidence boundary for a conservative Pizza V1 workflow. It does not define recipes and does not claim experimental validation. Its purpose is to say what Glutenix can safely treat as literature-informed, what is only heuristic, and what must be flagged as out-of-distribution for Pizza V1.

## Scope

Pizza V1 is a digital screening target for gluten-free pizza-like dough and crust systems. Current support comes from working notes in `docs/application-targets-research.md` and the heuristic target profile in `glutenix/engine/targets.py`.

No structured `data/literature/pizza_baking.jsonl` dataset exists yet. Therefore Pizza V1 must remain `heuristic` or `literature_informed`, never `calibrated`.

## Source Inventory

| Source | Type | Current Use | Evidence Level | Confidence Tier |
|---|---|---|---|---|
| Dey et al. 2023, `10.1007/s13197-022-05596-w` | Original research | 3D-printed gluten-free pizza dough and baked crust formula/process/texture anchor | Moderate for the exact rice/tapioca/sorghum/xanthan system; weak for general pizza | `literature_informed` |
| Pasqualone et al. 2022, `10.3390/foods11030482` | Original research | Rice/corn/lentil gluten-free pizza formula and nutrition/sensory anchor | Moderate for rice/corn/lentil systems; weak for other protein enrichments | `literature_informed` |
| `docs/application-targets-research.md#pizza-gluten-free` | Working target note | Initial blend/process scoring ranges | Weak until backed by structured pizza records | `heuristic` |
| `glutenix.engine.targets` Pizza profile | Internal heuristic target | Current optimizer target ranges for process/blend scoring | Weak | `heuristic` |

## Variable Inventory

All ranges below are audit ranges, not recommendations. A candidate outside these ranges may still rank well numerically, but Pizza V1 should mark it as heuristic or OOD until structured pizza records exist.

| Variable | Supported Range Or Anchor | Source Type | Evidence Level | Confidence Tier | Notes |
|---|---:|---|---|---|---|
| Main flour/starch family | Rice/tapioca/sorghum/xanthan; rice/corn/corn starch/lentil/psyllium/HPMC | Original research | Moderate | `literature_informed` | Other families are not Pizza V1-supported by current repo notes. |
| Rice flour | 20-30 g/100 g dough in Pasqualone; brown/sweet brown rice in Dey blend | Original research | Moderate | `literature_informed` | Dey blend uses specific rice types not fully represented in current ingredient DB. |
| Tapioca starch | 25% of Dey GF flour blend | Original research | Weak-moderate | `literature_informed` | One source only. |
| Sorghum flour | 25% of Dey GF flour blend | Original research | Weak-moderate | `literature_informed` | One source only. |
| Corn flour | 7.5 g/100 g dough | Original research | Moderate | `literature_informed` | Pasqualone only. |
| Corn starch | 7.5 g/100 g dough | Original research | Moderate | `literature_informed` | Pasqualone only. |
| Lentil flour | 0 or 10 g/100 g dough | Original research | Moderate | `literature_informed` | Native and extruded-cooked lentil variants are distinct. Other legumes are unsupported. |
| Water, dough basis | 48-55.6 g/100 g dough | Original research | Moderate | `literature_informed` | Dey: 55.6; Pasqualone: 48-53. |
| Approximate water/dry-blend ratio | About 1.03-1.34 water per main dry blend | Derived from original research | Weak-moderate | `literature_informed` | Recomputed from reported formula tables; not a calibrated hydration curve. |
| Oil/fat addition | 1.4 g/100 g dough | Original research | Weak | `literature_informed` | Dey only. Pasqualone formula excerpt in repo does not list oil. |
| Yeast | 0.3-1.0 g/100 g dough | Original research | Weak-moderate | `literature_informed` | Two sources, different systems. No dose-response curve. |
| Salt | 0.3-1.5 g/100 g dough | Original research | Weak-moderate | `literature_informed` | Two sources, different systems. |
| Sugar | 0.6 g/100 g dough | Original research | Weak | `literature_informed` | Dey only. |
| Emulsifier | 0.2 g/100 g dough | Original research | Weak | `literature_informed` | Dey only. Specific emulsifier behavior is not modeled. |
| Xanthan gum | 0.1% of Dey GF flour blend | Original research | Weak | `literature_informed` | One low-dose source only. Current target profile permits much higher hydrocolloid totals and is heuristic. |
| Psyllium | 1.5 g/100 g dough | Original research | Moderate | `literature_informed` | Pasqualone only. |
| HPMC | 0 or 1.0 g/100 g dough | Original research | Moderate | `literature_informed` | Pasqualone control includes HPMC; lentil variants remove it. |
| Fermentation time/temp | 120 min at 37 C for Dey GF dough | Original research | Weak | `literature_informed` | Only one explicit GF pizza fermentation anchor currently in repo notes. |
| Baking time/temp | 10 min at 204.4 C for Dey GF crust | Original research | Weak | `literature_informed` | Only one explicit baking anchor currently in repo notes. |
| Crust texture | Dey reports hardness, fracturability, springiness, cohesiveness, chewiness, resilience | Original research | Weak | `literature_informed` | No simulator comparison yet; units/method need extraction before calibration. |
| Nutrition/sensory | Pasqualone reports improved nutrition and acceptable sensory quality for lentil variants | Original research | Weak-moderate | `literature_informed` | Current repo notes do not contain full sensory table values. |
| Flavor target | Mild cereal, some toasted, low bitterness/earthiness | Internal heuristic | Weak | `heuristic` | No Pizza V1 sensory calibration yet. |
| Current blend score ranges | water_absorption 1.2-1.9, viscosity_index 1.4-2.8, hydrocolloid_pct 1-4%, fiber 2-8%, fat 0.5-6% | Working target note | Weak | `heuristic` | Useful for digital screening, not literature-calibrated pizza limits. |

## Pizza V1 Boundary Statements

These are conservative evidence boundaries for #87. They should be used to label candidates, not to claim validity.

- Pizza V1 can be treated as literature-informed only for rice/corn/tapioca/sorghum/lentil systems similar to Dey 2023 or Pasqualone 2022.
- Pizza V1 has no calibrated pizza simulator or pizza JSONL dataset; all pizza outputs remain non-calibrated.
- Hydration support is limited to the observed formula anchors: 48-55.6 g water per 100 g dough, or approximately 1.03-1.34 water per main dry blend after simple recomputation.
- Fermentation support is limited to the explicit Dey GF anchor: 120 min at 37 C. Other fermentation times/temperatures should be marked heuristic unless future pizza sources support them.
- Baking support is limited to the explicit Dey anchor: 10 min at 204.4 C. Higher-temperature or longer bake schedules should be marked heuristic/OOD until sourced.
- Hydrocolloid support is narrow: Dey low-dose xanthan, Pasqualone 1.5 g/100 g dough psyllium, and Pasqualone 0/1 g/100 g dough HPMC. General 1-4% hydrocolloid target ranges remain heuristic.
- Protein enrichment support is limited to 10 g/100 g dough lentil flour in Pasqualone. Other legumes, dairy proteins, isolates, and seed proteins are unsupported for Pizza V1.
- Sourdough pizza, long cold fermentation, high-temperature Neapolitan-style baking, high-hydration pizza above current anchors, egg/dairy-enriched pizza, and commercial flour mixes are outside Pizza V1 evidence boundaries.

## Known Gaps

- No structured `pizza_baking.jsonl` dataset.
- No row-level pizza calibration report.
- No simulator comparison against crust hardness, extensibility, bake loss, height, specific volume, color, or sensory scores.
- No source-backed range for high-temperature pizza baking.
- No source-backed range for long fermentation, cold fermentation, or sourdough.
- No structured evidence for handling/extensibility, topping hold, gumminess, crispness, or reheating behavior.
- No ingredient provenance for sweet brown rice flour, arrowroot-like ingredients, or specific lentil extrusion functionality.
- No source-level uncertainty model for translating dough-basis percentages to Glutenix dry-blend proportions.

## Implications For Pizza V1 Implementation

- #87 should add Pizza V1 diagnostics as evidence-aware screening, not as a validated recipe generator.
- Pizza V1 candidate output should use `confidence_summary=heuristic` by default and `ood_extrapolation` when outside the hard boundaries above.
- Any structured pizza dataset added later should preserve original formula basis and source table references before converting to Glutenix internal blend proportions.
- Bread evidence may inform mechanisms qualitatively, but it should not be counted as pizza coverage unless the source explicitly measures pizza dough or crust.
