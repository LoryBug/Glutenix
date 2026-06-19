# Bread Baking Literature Calibration Report

Date: 2026-06-19

This report compares the early `BreadQualitySimulator` against structured gluten-free bread literature records. It is diagnostic only: the bread model is new, the dataset is small, and no production calibration correction is applied.

## Sources

- Singh M, Adedeji AA. `Proso Millet Cultivar Effects on Rheology of Dough and Quality Characteristics of Gluten-Free Breads`. Foods, 2026, 15(10):1711.
- DOI: `10.3390/foods15101711`
- PMCID: `PMC13206684`
- URL: `https://pmc.ncbi.nlm.nih.gov/articles/PMC13206684/`
- Torres-Perez R, Siguero-Tudela MM, Domenech T, Garcia-Segovia P, Martinez-Monzo J, Igual M. `Effect of Additive Removal on the Physicochemical Properties of Gluten-Free Bread`. Foods, 2026, 15(2):338.
- DOI: `10.3390/foods15020338`
- PMCID: `PMC12841426`
- URL: `https://pmc.ncbi.nlm.nih.gov/articles/PMC12841426/`
- Loncaric P, Jukic M, Cozmuta AM, et al. `FTIR-Based Study of Starch Retrogradation and Protein Structure in Chickpea-Enriched Gluten-Free Bread During Storage`. Foods, 2026, 15(3):412.
- DOI: `10.3390/foods15030412`
- PMCID: `PMC12897030`
- URL: `https://pmc.ncbi.nlm.nih.gov/articles/PMC12897030/`

## Dataset

Records: 15

Sources: 3

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

## Error Summary

| Metric | Records | MAE | RMSE | Bias |
|---|---:|---:|---:|---:|
| `specific_volume_cm3_g` | 15 | 0.2042 | 0.264 | -0.042 |
| `crumb_hardness_n` | 2 | 1.9026 | 1.9057 | 0.1078 |

The specific-volume result is useful as an initial diagnostic, but it should not be overinterpreted. Nine millet records share the same generic `Millet flour` mapping, so cultivar-level variation is mostly invisible to the current model.

The crumb-hardness result is based on only two records and should be treated as a sanity check, not validation.

## Record Groups

By process family:

| Process family | Records |
|---|---:|
| `commercial_mix_bread` | 4 |
| `millet_cultivar_bread` | 9 |
| `protein_enriched_bread` | 2 |

By source:

| Source | Records |
|---|---:|
| `10.3390/foods15101711` | 9 |
| `10.3390/foods15020338` | 4 |
| `10.3390/foods15030412` | 2 |

## Rows

| ID | Measured volume | Simulated volume | Measured hardness | Simulated hardness | Process family |
|---|---:|---:|---:|---:|---|
| `singh_2026_millet_cope` | 2.19 | 2.2184 | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_dawn` | 2.22 | 2.2184 | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_sunrise` | 2.17 | 2.2184 | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_earlybird` | 2.4 | 2.2184 | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_huntsman` | 2.29 | 2.2184 | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_minco` | 2.32 | 2.2184 | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_panhandle` | 2.37 | 2.2184 | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_plateau` | 1.97 | 2.2184 | None | None | `millet_cultivar_bread` |
| `singh_2026_millet_rise` | 2.43 | 2.2184 | None | None | `millet_cultivar_bread` |
| `torres_2026_rf` | 3.0 | 2.8421 | None | None | `commercial_mix_bread` |
| `torres_2026_fa` | 2.9 | 2.7494 | None | None | `commercial_mix_bread` |
| `torres_2026_fb` | 2.8 | 2.5801 | None | None | `commercial_mix_bread` |
| `torres_2026_fc` | 3.3 | 2.702 | None | None | `commercial_mix_bread` |
| `loncaric_2026_rfb` | 1.93 | 2.2925 | 6.15 | 8.1604 | `protein_enriched_bread` |
| `loncaric_2026_cfb` | 1.65 | 2.1786 | 15.92 | 14.1252 | `protein_enriched_bread` |

## Interpretation

The bread model is now connected to real measured bread outcomes, but it remains early-stage.

The model captures approximate volume scale across three families: millet-corn starch bread, commercial bread mix treatments, and protein-enriched rice/chickpea/whey bread. The weakest point is source-specific detail: commercial mixes are aggregate-mapped, and millet cultivar differences are collapsed into one generic millet ingredient.

This means Glutenix can now say more than “bread is heuristic”, but it still cannot claim broad bread validation.

## Immediate Improvements

1. Add bread papers where HPMC, xanthan, psyllium, or guar levels are varied explicitly.
2. Add papers with table values for crumb hardness over storage.
3. Extract cultivar-specific millet composition from supplementary files if available.
4. Replace commercial aggregate mix records with papers that disclose full formula proportions.
5. Add literature-derived coverage ranges to `model_confidence` and OOD warnings.

## Limitations

- The model is diagnostic only and applies no fitted correction.
- The dataset is still small: 15 records from 3 papers.
- Specific volume is the only broadly covered metric.
- Hardness has only two records.
- Some records use approximate ingredient mapping due incomplete published formula disclosure.
- The current model does not represent cultivar-specific starch functionality unless it is encoded in seed ingredient properties.
