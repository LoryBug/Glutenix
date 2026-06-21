# Literature Triage for Gluten-Free Formulation Data

Date: 2026-06-20

This document records the issue #20 research pass for literature sources that could improve Glutenix. It is a triage document, not an extraction record. Candidate papers still need PDF/table verification before adding records to `data/literature/*.jsonl` or seed ingredient parameters.

## Scope

The search prioritized papers with extractable quantitative tables for:

- bread calibration: formula, process, specific volume, loaf volume, bake loss, moisture, water activity, crumb hardness, TPA, porosity, color, sensory, rheology
- pasta calibration: formula, process, cooking loss, optimal cooking time, water absorption, swelling, firmness, TPA, color, sensory, extrusion and drying parameters
- ingredient parameters: proximate composition, starch, protein, fat, fiber, ash, moisture, amylose, gelatinization, water absorption, WAI/WSI, pasting, rheology, hydrocolloid behavior
- sensory/application targets: acceptability, sensory descriptors, target ranges, product class suitability

## Classification

| Class | Meaning |
|---|---|
| `calibration-ready` | Has endpoint metrics directly comparable to existing simulators plus usable formula/process detail. |
| `ingredient-parameter` | Has composition or functionality data useful for seed ingredient parameters or blend feature logic. |
| `sensory/target` | Useful for application targets or acceptability, but not direct simulator calibration. |
| `background only` | Mechanistic or review context without structured extraction-ready data. |

## Immediate Conclusions

- The merged ML residual benchmark (#18/#19) showed that residual ML should not be integrated yet. This triage supports that decision: the highest-value next step is more structured literature data.
- The strongest extraction targets are row-level response-surface, mixture-design, or factorial papers with formula/process and measured endpoints.
- Quiñones et al. 2015 is new to the project and useful, but likely as `sensory/target` or `ingredient-parameter`, not as direct simulator calibration unless the PDF has objective bread/pasta process endpoints.
- Follow-up extraction should happen in small batches by mechanism, not as one large data dump.

## Top Extraction Shortlist

| Priority | Paper | Domain | Class | Why First |
|---:|---|---|---|---|
| 1 | Ghodosipoor et al. 2025, quinoa bread with microbial transglutaminase and HPMC, DOI `10.1002/fsn3.70891` | Bread | `calibration-ready` | 13-run design with HPMC/TG, specific volume, moisture, hardness, acceptability, and validation data. |
| 2 | Bianchi et al. 2026, tapioca starch and red lentil GF bread, DOI `10.3390/foods15071230` | Bread | `calibration-ready` | Mixture design with volume, height, baking loss, TPA, pore metrics, moisture, aw, and pGI. |
| 3 | Bouasla & Wojtowicz 2019, rice-buckwheat extrusion pasta, DOI `10.3390/foods8100496` | Pasta | `calibration-ready` | Factorial extrusion process data with cooking loss, texture, WAC, color, sensory, and optimized conditions. |
| 4 | Pasini et al. 2025, tomato/linseed by-product GF pasta, DOI `10.1002/fsn3.71105` | Pasta | `calibration-ready` | Modern ingredient dose-response with cooking loss, water absorption, firmness, color, starch fractions, and pGI. |
| 5 | Sanchez et al. 2002, cornstarch/rice/cassava GF bread optimization, DOI `10.1111/j.1365-2621.2002.tb11420.x` | Bread | `calibration-ready` | Simple starch/flour system valuable for starch-type and optimizer sanity checks. |
| 6 | Sciarini et al. 2010, gluten-free flours and mixtures, DOI `10.1007/s11947-008-0098-2` | Bread | `calibration-ready` | Bridges flour mixture properties, batter behavior, and bread quality. |
| 7 | Marco & Rosell 2008, protein-enriched GF composite flours, DOI `10.1016/j.jfoodeng.2008.01.018` | Ingredient | `ingredient-parameter` | Useful for protein-source functionality and seed parameters. |
| 8 | Quiñones et al. 2015, composite flour blends, DOI `10.7603/s40934-015-0003-3` | Ingredient/Targets | `sensory/target` | New composite flour blend evidence for rice, potato, cassava, millet, and corn blends. |

## Bread Candidates

| Paper | Class | Likely Extractable Data | Use In Glutenix | Priority |
|---|---|---|---|---|
| Ghodosipoor et al. 2025, `Optimization of Quinoa-Based Gluten-Free Bread Production Using Microbial Transglutaminase Enzyme and HPMC by RSM`, DOI `10.1002/fsn3.70891`, PMCID `PMC12400160` | `calibration-ready` | HPMC/TG design, specific volume, moisture, hardness, acceptability, optimized/control validation | Adds quinoa, enzyme, and HPMC dose-response to bread calibration | High |
| Rodriguez-Espana et al. 2025, whole sorghum GF bread RSM, DOI `10.3390/foods14173113`, PMCID `PMC12427757` | `calibration-ready` | specific loaf volume, crumb firmness, sensory, proximate composition, water/yeast/sugar/psyllium/xanthan/lecithin factors | Adds sorghum and multi-factor bread optimization | High |
| Di Renzo et al. 2024, quinoa dough/bread hydrocolloids, DOI `10.3390/foods13091382`, PMCID `PMC11083858` | `calibration-ready` | farinograph, gas retention, specific volume, bake loss, aw, moisture, color, height, crumb image metrics | Strong HPMC/xanthan/alginate/carrageenan comparison | High |
| Bianchi et al. 2026, tapioca starch and red lentil GF bread, DOI `10.3390/foods15071230`, PMCID `PMC13072981` | `calibration-ready` | volume, height, baking loss, hardness, springiness, cohesiveness, chewiness, pore density/area, moisture, aw, pGI | Adds tapioca and lentil protein/starch effects | High |
| Abdollahzadeh et al. 2023/2024, HPMC/pectin/raisin juice in rice/foxtail millet bread, DOI `10.1002/fsn3.3741`, PMCID `PMC10804086` | `calibration-ready` | water absorption, farinograph, specific volume, porosity, moisture, color, firmness over storage, sensory | Adds foxtail millet, pectin, humectant, and storage effects | High |
| Sciarini et al. 2023, Gleditsia galactomannans in GF bread, DOI `10.3390/foods12040756`, PMCID `PMC9956313` | `ingredient-parameter` | batter rheology, volume, crumb cell metrics, firmness/chewiness over storage, aw | Links hydrocolloid rheology to bread quality | High |
| Bieniek & Buksa 2024, oat beta-glucans in GF bread, DOI `10.3390/molecules29194579`, PMCID `PMC11478284` | `ingredient-parameter` | water addition, baking loss, bread volume, hardness/adhesiveness, crumb moisture | Adds molar-mass and water-binding effects | Medium |
| Krolak et al. 2025, potato and cricket protein GF bread, DOI `10.3390/foods14111959`, PMCID `PMC12153992` | `calibration-ready` | proximate composition, aw, loaf volume, baking/cooling loss, NMR water mobility, TPA | Adds protein-source/water mobility evidence | Medium |
| Torres-Perez et al. 2024, HPMC/psyllium/xanthan bread, DOI `10.3390/foods13111691`, PMCID `PMC11172051` | `calibration-ready` | dough rheology, extrusion force, moisture, aw, pH, color, TPA, image cell metrics | Extends existing hydrocolloid space beyond current Torres 2026 data | High |
| Sanchez et al. 2002, cornstarch/rice/cassava GF bread optimization, DOI `10.1111/j.1365-2621.2002.tb11420.x` | `calibration-ready` | specific volume, crumb-grain score, bread score, response-surface optimum | Simple starch/flour calibration baseline | High |
| Sciarini et al. 2010, gluten-free flours and mixtures, DOI `10.1007/s11947-008-0098-2` | `calibration-ready` | batter properties, bread volume, texture, likely moisture/firmness | Bridge from ingredient mixture to batter and bread endpoints | High |
| Lazaridou et al. 2007, hydrocolloids and bread quality, DOI `10.1016/j.jfoodeng.2006.03.032` | `calibration-ready` | hydrocolloid dose, dough rheology, loaf volume, crumb firmness/texture | Foundational hydrocolloid calibration | High |
| Minarro et al. 2012, legume flours in GF bread, DOI `10.1016/j.jcs.2012.04.012` | `calibration-ready` | legume substitution, loaf volume, crumb texture, color, likely sensory | Broad legume baseline beyond chickpea/pea | High |
| Wolter et al. 2019, fermented faba bean GF bread, DOI `10.3390/foods8100431` | `calibration-ready` | faba bean fermentation, texture, structure, nutrition | Adds protein pre-treatment and fermentation effects | High |
| Abebe et al. 2023, white sorghum GF bread, DOI `10.3390/foods12224113` | `calibration-ready` | sorghum level, physicochemical quality, texture/color, sensory | Adds cereal substitution curve and sensory target | High |
| Santos et al. 2018, chickpea-based GF bread mixture design, DOI `10.1111/1750-3841.14009` | `calibration-ready` | loaf volume, crumb firmness/moisture, acceptability, ash/protein/fiber | Adds chickpea/starch blend mixture-design data | High |
| Fratelli et al. 2018, psyllium and water in GF bread, DOI `10.1016/j.jff.2018.01.015` | `calibration-ready` | psyllium, hydration, volume/firmness/moisture, glycemic response | Directly strengthens hydration and psyllium logic | Medium |

## Pasta Candidates

| Paper | Class | Likely Extractable Data | Use In Glutenix | Priority |
|---|---|---|---|---|
| Bouasla & Wojtowicz 2019, rice-buckwheat pasta extrusion, DOI `10.3390/foods8100496`, PMCID `PMC6835652` | `calibration-ready` | cooking loss, hardness, firmness, stickiness, WAC, expansion, color, sensory, process factors | Adds extrusion process-response calibration | High |
| Bouasla & Wojtowicz 2021, rice instant pasta extrusion, DOI `10.3390/pr9040693` | `calibration-ready` | cooking time, WAC, cooking loss, hardness/firmness, stickiness, SME, microstructure | Isolates rice-pasta process effects | High |
| Bolarinwa & Oyesiji 2021, rice-soy pasta, DOI `10.1016/j.heliyon.2021.e06052`, PMCID `PMC7848634` | `calibration-ready` | cooking time, cooking loss, color, TPA, sensory, proximate composition | Adds soy flour/tapioca gradient, distinct from soy isolate spaghetti | High |
| Llavata et al. 2019/2020, tiger nut/chickpea/fenugreek fresh pasta, DOI `10.3390/foods9010011`, PMCID `PMC7022698` | `calibration-ready` | cooking loss, swelling, rheology, color, sensory/nutrition, pGI | Adds fiber-rich fresh pasta and natural hydrocolloid effects | High |
| Cervini et al. 2021, resistant starch sorghum in GF pasta, DOI `10.3390/foods10050908`, PMCID `PMC8143101` | `calibration-ready` | optimal cooking time, cooking loss, firmness, stickiness, color, sensory, resistant starch, hydrolysis index | Adds resistant starch dose-response | High |
| Pasini et al. 2025, tomato/linseed by-products in GF pasta, DOI `10.1002/fsn3.71105`, PMCID `PMC12535249` | `calibration-ready` | water absorption, cooking loss, color, firmness, adhesiveness, fiber, starch fractions, pGI | Adds modern fiber/protein/lipid perturbations | High |
| Sarker et al. 2026, tomato/soy GF noodles, DOI `10.1002/fsn3.71944`, PMCID `PMC13238788` | `calibration-ready` | WAC, cooking yield/loss, TPA, color, pH, sensory, nutrition/minerals, antioxidants | Adds millet noodle and tomato/soy effects | High |
| Ainsa et al. 2021, fish by-product enriched GF pasta, DOI `10.3390/foods10123049`, PMCID `PMC8701056` | `calibration-ready` | optimal cooking time, TPA, color, weight gain, swelling, cooking loss, moisture, sensory | Adds non-plant protein/fat perturbation | Medium |
| Faheid et al. 2022, CMC and psyllium in GF pasta, DOI `10.21603/2308-4057-2022-2-540` | `calibration-ready` | color, hardness/texture, cooking quality, nitrogen loss, sensory | Direct hydrocolloid binder comparison | Medium |
| Schoenlechner et al. 2010, amaranth/quinoa/buckwheat pasta, DOI `10.1007/s11130-010-0194-0` | `calibration-ready` | pseudocereal type, cooking quality, texture, functional/nutritional properties | Foundational pseudocereal comparison | Medium |
| Laleg et al. 2016, rice pasta enriched with legume flours, DOI `10.1016/j.lwt.2016.10.005` | `calibration-ready` | legume type/level, physical properties, texture, sensory, microstructure | Extends legume pasta beyond soy isolate | High |
| Laleg et al. 2016, 100% legume GF pasta, DOI `10.1371/journal.pone.0160721` | `calibration-ready` | legume species, cooking quality, firmness, protein, antinutrients, structure | Boundary case for high-protein pasta | High |
| Larrosa et al. 2020, xanthan/cassava GF pasta, DOI `10.1016/j.lwt.2020.109674` | `calibration-ready` | xanthan level, cassava starch pasta, cooking quality, texture, sensory | Adds cassava/xanthan pasta behavior | Medium |

## Ingredient And Target Candidates

| Paper | Class | Likely Extractable Data | Use In Glutenix | Priority |
|---|---|---|---|---|
| Quiñones et al. 2015, composite flour blends, DOI `10.7603/s40934-015-0003-3` | `sensory/target` / `ingredient-parameter` | blend formulations, proximate composition, crude gluten, sensory scores | Adds rice/potato/cassava/millet/corn composite blend evidence | Medium |
| Marco & Rosell 2008, protein-enriched GF composite flours, DOI `10.1016/j.jfoodeng.2008.01.018` | `ingredient-parameter` | water binding, functional/rheological properties, protein enrichment effects | Improves protein-source parameters and protein-enriched behavior | High |
| Mancebo et al. 2015, HPMC/psyllium/water rheology, DOI `10.1016/j.jcs.2014.10.005` | `ingredient-parameter` | dough rheology, water level effects, HPMC/psyllium interaction | Improves hydration and hydrocolloid parameters | Medium |
| Mariotti et al. 2009, corn starch/amaranth/pea isolate/psyllium doughs, DOI `10.1016/j.foodres.2009.04.017` | `ingredient-parameter` | dough rheology, ultrastructure, protein/fiber/starch interactions | Adds amaranth/pea/psyllium functionality evidence | Medium |
| Sandri et al. 2017, chia flour GF bread, DOI `10.1002/fsn3.495` | `sensory/target` | loaf volume, crumb firmness/moisture, acceptability, proximate composition | Useful if chia/seed flours are added | Low |
| Marti & Pagani 2013, gluten replacement in GF pasta, DOI `10.1016/j.tifs.2013.03.001` | `background only` | mechanism taxonomy for pasta structure | Helps interpret pasta model features, not extraction data | Low |
| Foschia et al. 2017, legumes in GF bakery/pasta, DOI `10.1146/annurev-food-030216-030045` | `background only` / `ingredient-parameter` | legume protein/starch/fiber quality tradeoffs | Cross-product ingredient rationale | Low |

## Recommended Follow-Up Issues

1. **Extract remaining starch/legume bread mixture-design records**: Sanchez 2002 and Santos 2018 if individual response values can be recovered. Bianchi 2026 is already structured in `bread_baking.jsonl`.
2. **Expand bread texture coverage**: prioritize papers with table-backed crumb hardness/firmness, because Di Renzo 2024 adds useful hydrocolloid volume/bake-loss data but no crumb-hardness table.
3. **Extract pasta process-response records**: Bouasla & Wojtowicz 2019 and 2021. Focus on extrusion moisture, temperature, screw speed, cooking loss, texture, WAC.
4. **Extract protein/fiber-enriched pasta records**: Pasini 2025, Bolarinwa & Oyesiji 2021, Laleg 2016. Focus on ingredient substitution, cooking loss, firmness, water absorption, sensory.
5. **Extract ingredient-parameter records**: Marco & Rosell 2008, Quiñones 2015, Mancebo 2015. Focus on water binding, proximate composition, rheology, hydrocolloid/protein parameters.

## Validation Plan

- For each follow-up extraction issue, verify that the full paper/PDF contains tables with usable numeric values before editing JSONL datasets.
- Keep each extraction issue to a coherent mechanism or product family.
- Re-run relevant report generation after each data batch.
- Do not integrate residual ML correction until source-level CV shows consistent improvement over the heuristic baseline.
