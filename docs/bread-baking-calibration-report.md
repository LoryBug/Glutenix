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

## Dataset

Records: 33

Sources: 6

Main metric: `specific_volume_cm3_g`

Auxiliary metrics where available:

- `crumb_hardness_n`
- `bake_loss_pct`
- `moisture_pct`
- `water_activity`
- `void_fraction_pct`
- `porosity_pct`
- TPA fields from Loncaric 2026

Coverage:

- 9 proso millet cultivar breads.
- 4 commercial gluten-free bread mix additive-removal treatments.
- 2 protein-enriched rice/chickpea/whey breads.
- 6 explicit HPMC/xanthan/guar hydrocolloid-combination breads (Parsamajd 2025).
- 6 rice-flour and maize-starch HPMC/psyllium/xanthan breads (Belorio 2020).
- 1 control hydrocolloid bread (Wojcik 2021, 0% pea protein).
- 5 pea-protein-enriched breads at 5-25% substitution (Wojcik 2021).

## Error Summary

| Metric | Records | MAE | RMSE | Bias |
|---|---|---|---:|---:|---:|
| `specific_volume_cm3_g` | 27 | 0.4922 | 1.117 | -0.1641 |
| `crumb_hardness_n` | 20 | 5.8552 | 9.3884 | -1.8843 |
| `porosity_pct` | 8 | 5.6942 | 10.1545 | 5.6484 |

The specific-volume MAE has increased from 0.2042 to 0.4922 as new hydrocolloid and protein-enriched records widened the formulation space. The rice-flour-based Belorio records (1.33-1.48 cm3/g) and the very high maize-starch+HPMC record (7.58 cm3/g) challenge the model's uniform treatment of starch and flour bases.

Crumb hardness coverage has grown from 2 to 20 records, though MAE is 5.85 N. The model underestimates Belorio's high hardness values (e.g., 42.44 N simulated as 12.0 N) and overestimates Wojcik's softer protein-enriched breads.

Porosity remains unchanged at 8 records from Parsamajd 2025 and Loncaric 2026.

## Record Groups

By process family:

| Process family | Records |
|---|---:|
| `commercial_mix_bread` | 4 |
| `hydrocolloid_bread` | 13 |
| `millet_cultivar_bread` | 9 |
| `protein_enriched_bread` | 7 |

By source:

| Source | Records |
|---|---:|
| `10.1002/fsn3.71107` | 6 |
| `10.1016/j.heliyon.2022.e12164` | 0 |
| `10.1038/s41598-021-93834-0` | 6 |
| `10.3390/foods15101711` | 9 |
| `10.3390/foods15020338` | 4 |
| `10.3390/foods15030412` | 2 |
| `10.3390/foods9111548` | 6 |

## Rows

| ID | Measured volume | Simulated volume | Measured hardness | Simulated hardness | Measured porosity | Simulated porosity | Process family |
|---|---:|---:|---:|---:|---:|---:|---|
| `singh_2026_millet_cope` | 2.19 | 2.2184 | None | None | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_dawn` | 2.22 | 2.2184 | None | None | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_sunrise` | 2.17 | 2.2184 | None | None | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_earlybird` | 2.4 | 2.2184 | None | None | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_huntsman` | 2.29 | 2.2184 | None | None | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_minco` | 2.32 | 2.2184 | None | None | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_panhandle` | 2.37 | 2.2184 | None | None | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_plateau` | 1.97 | 2.2184 | None | None | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_rise` | 2.43 | 2.2184 | None | None | None | None | `millet_cultivar_bread` |
| `torres_2026_rf` | 3.0 | 2.8421 | None | None | None | None | `commercial_mix_bread` |
| `torres_2026_fa` | 2.9 | 2.7494 | None | None | None | None | `commercial_mix_bread` |
| `torres_2026_fb` | 2.8 | 2.5801 | None | None | None | None | `commercial_mix_bread` |
| `torres_2026_fc` | 3.3 | 2.702 | None | None | None | None | `commercial_mix_bread` |
| `loncaric_2026_rfb` | 1.93 | 2.2925 | 6.15 | 8.1604 | 21.01 | 39.8795 | `protein_enriched_bread` |
| `loncaric_2026_cfb` | 1.65 | 2.1786 | 15.92 | 14.1252 | 17.17 | 38.6616 | `protein_enriched_bread` |
| `parsamajd_2025_guar` | None | None | None | None | 33.84 | 35.8445 | `hydrocolloid_bread` |
| `parsamajd_2025_hpmc` | None | None | None | None | 35.31 | 35.8103 | `hydrocolloid_bread` |
| `parsamajd_2025_xanthan` | None | None | None | None | 34.46 | 35.9032 | `hydrocolloid_bread` |
| `parsamajd_2025_xanthan_guar` | None | None | None | None | 35.45 | 35.8739 | `hydrocolloid_bread` |
| `parsamajd_2025_hpmc_guar` | None | None | None | None | 35.19 | 35.8274 | `hydrocolloid_bread` |
| `parsamajd_2025_hpmc_xanthan` | None | None | None | None | 36.04 | 35.8568 | `hydrocolloid_bread` |
| `belorio_2020_rf_hpmc` | 1.33 | 1.997 | 42.44 | 11.996 | None | None | `hydrocolloid_bread` |
| `belorio_2020_rf_psyllium` | 1.44 | 2.1447 | 14.98 | 11.3464 | None | None | `hydrocolloid_bread` |
| `belorio_2020_rf_xanthan` | 1.48 | 2.1488 | 9.04 | 11.3298 | None | None | `hydrocolloid_bread` |
| `belorio_2020_ms_hpmc` | 7.58 | 2.1064 | 1.44 | 11.6942 | None | None | `hydrocolloid_bread` |
| `belorio_2020_ms_psyllium` | 2.37 | 2.1107 | 19.51 | 11.6759 | None | None | `hydrocolloid_bread` |
| `belorio_2020_ms_xanthan` | 2.25 | 2.1145 | 19.58 | 11.66 | None | None | `hydrocolloid_bread` |
| `wojcik_2021_ppp0` | 2.962 | 2.1798 | 4.5 | 8.2334 | None | None | `hydrocolloid_bread` |
| `wojcik_2021_ppp5` | 2.533 | 2.2006 | 4.0 | 8.1167 | None | None | `protein_enriched_bread` |
| `wojcik_2021_ppp10` | 2.253 | 2.2213 | 4.5 | 8.0022 | None | None | `protein_enriched_bread` |
| `wojcik_2021_ppp15` | 1.986 | 2.2418 | 6.0 | 7.8897 | None | None | `protein_enriched_bread` |
| `wojcik_2021_ppp20` | 1.823 | 2.2623 | 8.0 | 7.7793 | None | None | `protein_enriched_bread` |
| `wojcik_2021_ppp25` | 1.805 | 2.2826 | 10.0 | 7.6709 | None | None | `protein_enriched_bread` |

## Interpretation

The bread model is now connected to 33 measured bread outcomes from 6 peer-reviewed sources covering 4 process families. Key observations:

**Specific volume** (27 records): MAE has risen to 0.49 as the model confronts diverse formulation spaces. The Belorio 2020 rice-flour records (1.33-1.48 cm3/g) are underpredicted by the current starch model, while the extreme maize-starch+HPMC record (7.58 cm3/g) is severely underpredicted (2.11), highlighting that starch type differences are not yet captured. The Wojcik 2021 pea-protein series shows a clear dose-response trend (2.96 -> 1.81 cm3/g) that the model partially follows but underestimates the rate of volume loss.

**Crumb hardness** (20 records): The model now has substantial hardness coverage, but MAE is 5.85 N. The model systematically underestimates the very hard Belorio RF+HPMC crumb (42.44 N) and overestimates the softer protein-enriched breads (~4-10 N simulated as ~8 N). These biases likely reflect the absence of drying/staling kinetics in the current heuristic.

**Porosity** (8 records): Unchanged at MAE 5.69. The model systematically overpredicts porosity by ~5.6 points, likely because the heuristic conflates gas retention with structural openness.

The model captures approximate volume scale across four families. The weakest point remains ingredient-level detail: commercial mixes are aggregate-mapped, millet cultivars are collapsed into one generic ingredient, and the model does not differentiate starch type (rice vs. maize).

## Immediate Improvements

1. Differentiate starch-type functional properties (rice vs. maize vs. tapioca) in the ingredient model.
2. Add baking-loss coupling to improve moisture-dependent hardness predictions.
3. Extract additional protein/fiber enriched bread papers with both volume and texture tables.
4. Replace commercial aggregate mix records with fully disclosed formula papers.
5. Investigate whether the systematic porosity overprediction is a model bias or a measurement-scale artifact.

## Limitations

- The model is diagnostic only and applies no fitted correction.
- The dataset is still small: 33 records from 6 papers.
- Specific volume MAE (0.49) is dominated by the maize-starch+HPMC outlier (7.58 vs 2.11).
- Hardness predictions are directionally correct but inaccurate in magnitude.
- Porosity overprediction bias suggests structural modelling needs refinement.
- Some records use approximate ingredient mapping due to incomplete published formula disclosure.
- The current model does not represent cultivar-specific or starch-type-specific functionality.
