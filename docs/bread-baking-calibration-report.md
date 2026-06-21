# Bread Baking Literature Calibration Report

Date: 2026-06-20

This report compares the early `BreadQualitySimulator` against structured gluten-free bread literature records. It is diagnostic only: the bread model is new, the dataset is small, and no production calibration correction is applied.

## Sources

- Singh M, Adedeji AA. `Proso Millet Cultivar Effects on Rheology of Dough and Quality Characteristics of Gluten-Free Breads`. Foods, 2026, 15(10):1711.
  - DOI: `10.3390/foods15101711`
  - PMCID: `PMC13206684`
- Torres-Perez R, Siguero-Tudela MM, Domenech T, Garcia-Segovia P, Martinez-Monzo J, Igual M. `Effect of Additive Removal on the Physicochemical Properties of Gluten-Free Bread`. Foods, 2026, 15(2):338.
  - DOI: `10.3390/foods15020338`
  - PMCID: `PMC12841426`
- Loncaric P, Jukic M, Cozmuta AM, et al. `FTIR-Based Study of Starch Retrogradation and Protein Structure in Chickpea-Enriched Gluten-Free Bread During Storage`. Foods, 2026, 15(3):412.
  - DOI: `10.3390/foods15030412`
  - PMCID: `PMC12897030`
- Parsamajd S, et al. `Synergistic Effects of Hydrocolloid Combinations on Gluten-Free Batter and Bread Characteristics`. Food Science & Nutrition, 2025.
  - DOI: `10.1002/fsn3.71107`
  - PMCID: `PMC12540201`
- Belorio M, Gomez M. `Effect of Hydration on Gluten-Free Breads Made with Hydroxypropyl Methylcellulose in Comparison with Psyllium and Xanthan Gum`. Foods, 2020, 9(11):1548.
  - DOI: `10.3390/foods9111548`
  - PMCID: `PMC7693925`
- Wojcik M, Rozylo R, Schonlechner R, Berger MV. `Physico-chemical properties of an innovative gluten-free, low-carbohydrate and high protein-bread enriched with pea protein powder`. Scientific Reports, 2021, 11:14498.
  - DOI: `10.1038/s41598-021-93834-0`
  - PMCID: `PMC8280221`
- Kahraman G, Harsa S, Casiraghi MC, Lucisano M, Cappa C. `Impact of Raw, Roasted and Dehulled Chickpea Flours on Technological and Nutritional Characteristics of Gluten-Free Bread`. Foods, 2022, 11(2):199.
  - DOI: `10.3390/foods11020199`
  - PMCID: `PMC8774402`
- Bianchi F, et al. `Gluten-Free Bread with Tapioca Starch and Red Lentil Flour: A Mixture Design Approach`. Foods, 2026, 15(7):1230.
  - DOI: `10.3390/foods15071230`
  - PMCID: `PMC13072981`
- Ghodosipoor Z, Zahed O, Fallahzadeh H, Mollakhalili-Meybodi N, Nematollahi A. `Optimization of Quinoa-Based Gluten-Free Bread Production Using Microbial Transglutaminase Enzyme and Hydroxypropyl Methyl Cellulose (HPMC) by Response Surface Methodology`. Food Science & Nutrition, 2025.
  - DOI: `10.1002/fsn3.70891`
  - PMCID: `PMC12400160`

<!-- generated-start: bread-calibration-summary -->
## Dataset

Records: 65

Sources: 10

Main metric: `specific_volume_cm3_g`

Auxiliary metrics where available:

- `crumb_hardness_n`
- `bake_loss_pct`
- `moisture_pct`
- `water_activity`
- `void_fraction_pct`
- `porosity_pct`
- TPA fields from Loncaric 2026

Coverage by process family:

| Process family | Records |
|---|---:|
| `commercial_mix_bread` | 4 |
| `enzyme_bread` | 1 |
| `enzyme_hydrocolloid_bread` | 12 |
| `generic_gluten_free_bread` | 2 |
| `hydrocolloid_bread` | 21 |
| `millet_cultivar_bread` | 9 |
| `protein_enriched_bread` | 16 |

## Error Summary

| Metric | Records | MAE | RMSE | Bias |
|---|---:|---:|---:|---:|
| `specific_volume_cm3_g` | 59 | 0.4684 | 0.8476 | 0.0483 |
| `crumb_hardness_n` | 40 | 25.0772 | 38.5882 | -18.4493 |
| `porosity_pct` | 11 | 7.5321 | 10.8127 | 0.8222 |

## Record Groups

By process family:

| Process family | Records |
|---|---:|
| `commercial_mix_bread` | 4 |
| `enzyme_bread` | 1 |
| `enzyme_hydrocolloid_bread` | 12 |
| `generic_gluten_free_bread` | 2 |
| `hydrocolloid_bread` | 21 |
| `millet_cultivar_bread` | 9 |
| `protein_enriched_bread` | 16 |

By source:

| Source | Records |
|---|---:|
| `10.1002/fsn3.70891` | 15 |
| `10.1002/fsn3.71107` | 6 |
| `10.1038/s41598-021-93834-0` | 6 |
| `10.3390/foods11020199` | 3 |
| `10.3390/foods13091382` | 5 |
| `10.3390/foods15020338` | 4 |
| `10.3390/foods15030412` | 2 |
| `10.3390/foods15071230` | 9 |
| `10.3390/foods15101711` | 9 |
| `10.3390/foods9111548` | 6 |

## Rows

| ID | Measured volume | Simulated volume | Measured hardness | Simulated hardness | Measured porosity | Simulated porosity | Process family |
|---|---:|---:|---:|---:|---:|---:|---|
| `singh_2026_millet_cope` | 2.19 | 2.1988 | None | None | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_dawn` | 2.22 | 2.1988 | None | None | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_sunrise` | 2.17 | 2.1988 | None | None | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_earlybird` | 2.4 | 2.1988 | None | None | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_huntsman` | 2.29 | 2.1988 | None | None | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_minco` | 2.32 | 2.1988 | None | None | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_panhandle` | 2.37 | 2.1988 | None | None | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_plateau` | 1.97 | 2.1988 | None | None | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_rise` | 2.43 | 2.1988 | None | None | None | None | `millet_cultivar_bread` |
| `torres_2026_rf` | 3.0 | 2.8421 | None | None | None | None | `commercial_mix_bread` |
| `torres_2026_fa` | 2.9 | 2.7494 | None | None | None | None | `commercial_mix_bread` |
| `torres_2026_fb` | 2.8 | 2.5801 | None | None | None | None | `commercial_mix_bread` |
| `torres_2026_fc` | 3.3 | 2.702 | None | None | None | None | `commercial_mix_bread` |
| `loncaric_2026_rfb` | 1.93 | 2.0822 | 6.15 | 8.975 | 21.01 | 38.8702 | `protein_enriched_bread` |
| `loncaric_2026_cfb` | 1.65 | 2.0618 | 15.92 | 14.6111 | 17.17 | 38.1008 | `protein_enriched_bread` |
| `parsamajd_2025_guar` | None | None | None | None | 33.84 | 36.2331 | `hydrocolloid_bread` |
| `parsamajd_2025_hpmc` | None | None | None | None | 35.31 | 36.1989 | `hydrocolloid_bread` |
| `parsamajd_2025_xanthan` | None | None | None | None | 34.46 | 36.2917 | `hydrocolloid_bread` |
| `parsamajd_2025_xanthan_guar` | None | None | None | None | 35.45 | 36.2624 | `hydrocolloid_bread` |
| `parsamajd_2025_hpmc_guar` | None | None | None | None | 35.19 | 36.216 | `hydrocolloid_bread` |
| `parsamajd_2025_hpmc_xanthan` | None | None | None | None | 36.04 | 36.2453 | `hydrocolloid_bread` |
| `belorio_2020_rf_hpmc` | 1.33 | 1.7519 | 42.44 | 13.364 | None | None | `hydrocolloid_bread` |
| `belorio_2020_rf_psyllium` | 1.44 | 1.8996 | 14.98 | 16.4119 | None | None | `hydrocolloid_bread` |
| `belorio_2020_rf_xanthan` | 1.48 | 1.9037 | 9.04 | 14.429 | None | None | `hydrocolloid_bread` |
| `belorio_2020_ms_hpmc` | 7.58 | 2.2044 | 1.44 | 11.302 | None | None | `hydrocolloid_bread` |
| `belorio_2020_ms_psyllium` | 2.37 | 2.2087 | 19.51 | 15.2071 | None | None | `hydrocolloid_bread` |
| `belorio_2020_ms_xanthan` | 2.25 | 2.2125 | 19.58 | 13.2321 | None | None | `hydrocolloid_bread` |
| `wojcik_2021_ppp0` | 2.962 | 2.1566 | 4.5 | 11.3247 | None | None | `hydrocolloid_bread` |
| `wojcik_2021_ppp5` | 2.533 | 2.1786 | 4.0 | 8.2015 | None | None | `protein_enriched_bread` |
| `wojcik_2021_ppp10` | 2.253 | 2.2004 | 4.5 | 8.0806 | None | None | `protein_enriched_bread` |
| `wojcik_2021_ppp15` | 1.986 | 2.2222 | 6.0 | 7.9622 | None | None | `protein_enriched_bread` |
| `wojcik_2021_ppp20` | 1.823 | 2.2438 | 8.0 | 7.846 | None | None | `protein_enriched_bread` |
| `wojcik_2021_ppp25` | 1.805 | 2.2653 | 10.0 | 7.7321 | None | None | `protein_enriched_bread` |
| `kahraman_2022_cf` | 2.51 | 1.6641 | 13.37 | 16.9552 | 41.49 | 32.6118 | `protein_enriched_bread` |
| `kahraman_2022_rcf` | 2.89 | 1.6641 | 5.49 | 16.9552 | 51.41 | 32.6118 | `protein_enriched_bread` |
| `kahraman_2022_dcf` | 2.75 | 1.6641 | 14.05 | 16.9552 | 41.84 | 32.6118 | `protein_enriched_bread` |
| `bianchi_2026_s1` | 2.18 | 2.3289 | 2.93 | 11.1506 | None | None | `hydrocolloid_bread` |
| `bianchi_2026_s2` | 1.84 | 2.2632 | 8.09 | 14.6366 | None | None | `protein_enriched_bread` |
| `bianchi_2026_s3` | 2.12 | 2.2496 | 5.25 | 14.721 | None | None | `protein_enriched_bread` |
| `bianchi_2026_s4` | 2.07 | 2.3507 | 3.05 | 11.1146 | None | None | `hydrocolloid_bread` |
| `bianchi_2026_s5` | 2.1 | 2.3069 | 3.88 | 12.8724 | None | None | `protein_enriched_bread` |
| `bianchi_2026_s6` | 2.16 | 2.296 | 3.56 | 12.8921 | None | None | `protein_enriched_bread` |
| `bianchi_2026_s7` | 2.14 | 2.3401 | 3.35 | 11.1315 | None | None | `hydrocolloid_bread` |
| `bianchi_2026_s8` | 1.97 | 2.274 | 5.67 | 14.6163 | None | None | `protein_enriched_bread` |
| `bianchi_2026_s9` | 2.14 | 2.2753 | 1.83 | 12.9995 | None | None | `protein_enriched_bread` |
| `ghodosipoor_2025_r01` | 2.03 | 2.7212 | 68.063 | 9.1286 | None | None | `enzyme_hydrocolloid_bread` |
| `ghodosipoor_2025_r02` | 2.026 | 2.7212 | 66.5903 | 9.1286 | None | None | `enzyme_hydrocolloid_bread` |
| `ghodosipoor_2025_r03` | 1.89 | 2.7212 | 66.0929 | 9.1286 | None | None | `enzyme_hydrocolloid_bread` |
| `ghodosipoor_2025_r04` | 2.205 | 2.7212 | 69.0395 | 9.1286 | None | None | `enzyme_hydrocolloid_bread` |
| `ghodosipoor_2025_r05` | 2.087 | 2.7212 | 71.007 | 9.1286 | None | None | `enzyme_hydrocolloid_bread` |
| `ghodosipoor_2025_r06` | 2.5977 | 2.7212 | 53.6437 | 9.1286 | None | None | `hydrocolloid_bread` |
| `ghodosipoor_2025_r07` | 1.8473 | 2.6876 | 131.9171 | 9.7223 | None | None | `enzyme_bread` |
| `ghodosipoor_2025_r08` | 1.7463 | 2.6975 | 108.2154 | 9.5469 | None | None | `enzyme_hydrocolloid_bread` |
| `ghodosipoor_2025_r09` | 2.2836 | 2.7444 | 47.976 | 8.7173 | None | None | `enzyme_hydrocolloid_bread` |
| `ghodosipoor_2025_r10` | 2.1045 | 2.7212 | 56.3108 | 9.1286 | None | None | `enzyme_hydrocolloid_bread` |
| `ghodosipoor_2025_r11` | 1.9444 | 2.6975 | 87.3368 | 9.5469 | None | None | `enzyme_hydrocolloid_bread` |
| `ghodosipoor_2025_r12` | 2.3163 | 2.7444 | 40.9026 | 8.7173 | None | None | `enzyme_hydrocolloid_bread` |
| `ghodosipoor_2025_r13` | 2.466 | 2.7539 | 34.0761 | 8.5489 | None | None | `enzyme_hydrocolloid_bread` |
| `ghodosipoor_2025_f1_opt` | 2.34 | 2.7305 | 53.565 | 8.9631 | None | None | `enzyme_hydrocolloid_bread` |
| `ghodosipoor_2025_f2_control` | 1.78 | 2.6876 | None | None | None | None | `generic_gluten_free_bread` |
| `di_renzo_2024_control` | 1.59 | 1.7121 | None | None | None | None | `generic_gluten_free_bread` |
| `di_renzo_2024_kc` | 1.61 | 1.7855 | None | None | None | None | `hydrocolloid_bread` |
| `di_renzo_2024_xg` | 1.29 | 1.822 | None | None | None | None | `hydrocolloid_bread` |
| `di_renzo_2024_sa` | 1.7 | 1.7691 | None | None | None | None | `hydrocolloid_bread` |
| `di_renzo_2024_hpmc` | 2.29 | 1.8056 | None | None | None | None | `hydrocolloid_bread` |

<!-- generated-end: bread-calibration-summary -->

## Interpretation

The bread model is now connected to 65 measured bread outcomes from 10 peer-reviewed sources covering 7 process families. Key observations:

**Specific volume** (59 records): MAE is 0.4684. Ghodosipoor 2025 adds quinoa/HPMC/TG records and shifts one visible error toward overprediction for enzyme-treated quinoa breads. Di Renzo 2024 adds a separate quinoa/rice/potato hydrocolloid comparison where the simulator captures the broad volume scale but misses the full HPMC uplift and xanthan depression. The Kahraman 2022 chickpea-enriched records remain underpredicted, and the Belorio 2020 rice/HPMC and Wojcik 2021 pea-protein gaps remain useful diagnostics.

**Crumb hardness** (40 records): MAE is 25.08 N. The increase is driven by Ghodosipoor 2025, where measured hardness ranges from 34.08 to 131.92 N while the simulator predicts about 8.55-9.72 N for the quinoa/HPMC/TG system. This is evidence of an unmodeled enzyme/hydrocolloid/quinoa structure mechanism, not a reason to blindly fit a global hardness offset.

**Porosity** (11 records): MAE remains 7.53 with bias +0.82 because Ghodosipoor 2025 and Di Renzo 2024 do not provide table-backed porosity percentages in mapped records. The Kahraman records (41.5-51.4% measured vs 32.6% simulated) are underpredicted, partially offsetting the Loncaric overprediction. This bidirectional error suggests the porosity heuristic needs separate terms for hydrocolloid and protein contributions.

The model captures approximate volume scale across several families, but the Ghodosipoor tranche makes clear that enzyme-treated quinoa/HPMC breads are outside the current hardness mechanism. Di Renzo 2024 improves hydrocolloid ingredient coverage for potato starch, sodium alginate, and kappa carrageenan. The weakest points remain ingredient-level detail and process mechanism detail: TG enzyme dose is tracked but not modeled, commercial mixes are aggregate-mapped, millet cultivars are collapsed into one generic ingredient, and protein ingredient processing state is not represented.

## Post-Expansion Systematic Bias Review

This historical section documents the structured review performed after adding 12 new records from Belorio 2020 and Wojcik 2021 (issues #2, #3), 3 records from Kahraman 2022 (issue #9), and 9 records from Bianchi 2026 (issue #23). It predates the Ghodosipoor 2025 and Di Renzo 2024 issue #22 tranches. The current generated metrics above supersede the old counts; a heavier audit should refresh this cross-family bias review before more model changes.

### Volume bias by process family

| Family | n | Mean bias (sim - meas) | Direction |
|---|---|---|---:|
| `commercial_mix_bread` | 4 | -0.28 | Model slightly underpredicts |
| `hydrocolloid_bread` | 7 | -0.72 | Model notably underpredicts |
| `millet_cultivar_bread` | 9 | -0.06 | Excellent agreement |
| `protein_enriched_bread` | 10 | -0.19 | Mixed, near-centered |

The millet cultivar breads still show the best volume agreement. Protein-enriched bread average bias is near-centered because the Kahraman records (measured 2.51-2.89, simulated 1.66) are severely underpredicted, while Wojcik and Loncaric records remain partly overpredicted. This bidirectional error indicates the model lacks a general protein-source gas-retention factor.

### Hardness bias by process family

| Family | n | Mean bias (sim - meas) | Direction |
|---|---|---|---:|
| `hydrocolloid_bread` | 7 | -2.32 | Model underpredicts |
| `protein_enriched_bread` | 10 | +2.68 | Model overpredicts (mixed) |

Hardness coverage grew from 2 to 17 records. Protein-enriched bias shifted positive because the Kahraman records show mixed behavior: CF (13.37 vs 16.96) and DCF (14.05 vs 16.96) are moderately overpredicted, while RCF (5.49 vs 16.96) is severely overpredicted. This should be treated as evidence that processing state can matter, not as a reason to overfit the model to one ingredient family.

### Porosity bias by process family

| Family | n | Mean bias (sim - meas) | Direction |
|---|---|---|---:|
| `hydrocolloid_bread` | 6 | +1.19 | Close agreement |
| `protein_enriched_bread` | 5 | +0.38 | Mixed, near-centered |

Porosity bias for protein-enriched breads improved dramatically from strongly positive to near-centered. The Kahraman records (41.5-51.4% measured vs 32.6% simulated) are underpredicted by 8-19 points, partially offsetting the Loncaric overprediction (~20 points). This bidirectional error suggests that protein type and processing history substantially affect crumb porosity in ways the current hydrocolloid-driven heuristic cannot capture.

### Coverage alignment

The `model_confidence` coverage module correctly flags:
- **Covered ingredients**: 22 mapped ingredients appear in at least one bread record
- **Process families**: 7 bread families have records after separating TG enzyme-treated breads; no active Pane recipe lacks a family match
- **Risk flags**: Candidate recipes using sorghum flour, brown rice flour, or unlisted protein powders would be flagged as outside ingredient coverage

The coverage limitations in `coverage.py` remain directionally accurate: strongest for specific volume, limited for porosity, and hardness now broader but strongly biased for quinoa/HPMC/TG records. Di Renzo 2024 improves hydrocolloid breadth but does not add hardness values. Parsamajd 2025 still lacks table-backed specific volume, while Ghodosipoor 2025 adds HPMC/TG response data without giving the simulator an enzyme mechanism.

### Actionable findings

1. **Starch-type differentiation** — The maize-starch vs rice-flour gap is the single clearest modeling deficiency. Maize starch produces radically different volumes in Belorio 2020. A follow-up modeling issue should add starch-type functional parameters (rice, maize, tapioca) to `BlendProperties` and the bread simulator.

2. **Hardness prediction for hydrocolloid breads** — `BreadQualitySimulator` lacks hydrocolloid-specific texture effects. Creating a hydrocolloid viscosity-to-hardness mapping is warranted but requires more cross-study hardness data to avoid overfitting to Belorio alone.

3. **Protein-enriched porosity** — Protein enrichment severely alters crumb structure in ways the current model does not represent. Kahraman 2022 added 3 porosity records for chickpea-enriched breads, revealing that the porosity heuristic under-predicts chickpea protein systems even as it over-predicts whey/chickpea systems (Loncaric 2026). A protein-type-specific structural factor is needed.

4. **Protein source and processing state** — Protein-enriched records now show that source and processing history can change volume, hardness, and porosity even when formula ratios look similar. Any follow-up should model this as a general protein/processing feature, not a single-ingredient special case.

1. Differentiate starch-type functional properties (rice vs. maize vs. tapioca) in the ingredient model.
2. Add baking-loss coupling to improve moisture-dependent hardness predictions.
3. Extract additional protein/fiber enriched bread papers with both volume and texture tables.
4. Replace commercial aggregate mix records with fully disclosed formula papers.
5. Investigate the bidirectional porosity bias: protein-type-specific structural factors may be needed.
6. Track protein source and processing-state effects only where multiple sources support a general pattern.

## Limitations

- The model is diagnostic only and applies no fitted correction.
- The dataset is still small: 65 records from 10 papers.
- Specific volume MAE (0.4684) is driven by multiple family-specific errors, including quinoa/HPMC/TG overprediction and chickpea protein underprediction.
- Hardness predictions are no longer directionally reliable for all families; Ghodosipoor 2025 shows severe underprediction for quinoa/HPMC/TG breads.
- Porosity bias improved (+5.74 to +0.82) but MAE increased (5.74 to 7.53) as the model now both over- and under-predicts across different protein systems.
- Some records use approximate ingredient mapping due to incomplete published formula disclosure.
- The current model tracks but does not mechanistically model TG enzyme effects, protein processing state, cultivar-specific functionality, or full starch/hydrocolloid source-specific functionality.
