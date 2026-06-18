# Pasta Cooking Literature Calibration Report

Date: 2026-06-18

This report compares the current `PastaCookingSimulator` against literature cooking-loss values extracted from Lux et al. 2023, Liu et al. 2026, and Detchewa et al. 2016.

Source:

- Lux nee Bantleon T, Spillmann F, Reimold F, Erdos A, Lochny A, Floter E. `Physical quality of gluten-free doughs and fresh pasta made of amaranth`. Food Science & Nutrition, 2023, 11(6):3213-3223.
- DOI: `10.1002/fsn3.3301`
- PMCID: `PMC10261804`
- URL: `https://pmc.ncbi.nlm.nih.gov/articles/PMC10261804/`
- Liu Q, Zhang S, Lin C, et al. `Synergistic effects of konjac glucomannan and curdlan on the qualities and starch digestibility of extruded gluten-free rice pasta`. Food Chemistry X, 2026, 33:103403.
- DOI: `10.1016/j.fochx.2025.103403`
- PMCID: `PMC12769803`
- URL: `https://pmc.ncbi.nlm.nih.gov/articles/PMC12769803/`
- Detchewa P, Thongngam M, Jane JL, Naivikul O. `Preparation of gluten-free rice spaghetti with soy protein isolate using twin-screw extrusion`. Journal of Food Science and Technology, 2016, 53(9):3485-3494.
- DOI: `10.1007/s13197-016-2323-8`
- PMCID: `PMC5069250`
- URL: `https://pmc.ncbi.nlm.nih.gov/articles/PMC5069250/`

## Dataset

Records: 40

Metric used for calibration: `cooking_loss_pct`

Auxiliary extracted metrics:

- `water_absorption_pct`
- `swelling_index`

Coverage:

- Amaranth flour:water ratios: `1:2`, `1:4`, `1:6`, `1:8`, `1:10`
- Sodium alginate levels: `1.0%`, `1.5%`
- Cooking times: `5`, `10`, `15` min
- Source tables: `Table 2a`, `Table 2b`
- Extruded dried high-amylose rice pasta: RF, RF+KGM, RF+KGM+CUD 1/2/3%
- Extruded dried high-amylose/waxy rice spaghetti: SPI 0/2.5/5/7.5/10%
- Liu water absorption was converted from `M2/M1*100` to net uptake by subtracting `100`.
- Detchewa water adsorption index is retained but not included in `water_absorption_pct` summary because its scale differs strongly from the current simulator target.

Mapped ingredients:

- `amaranth_flour` -> `Amaranth flour`.
- `sodium_alginate` -> `Sodium alginate`.
- `high_amylose_rice_flour` -> `High-amylose rice flour`.
- `konjac_glucomannan` -> `Konjac glucomannan`.
- `curdlan` -> `Curdlan`.
- `soy_protein_isolate` -> `Soy protein isolate`.

These are direct mappings after adding the missing literature ingredients to the database seed.

## Error Summary

| Stage | MAE | RMSE | Bias |
|---|---:|---:|---:|
| Before correction | 1.1078 | 1.3647 | 0.2267 |
| After linear correction | 1.1302 | 1.3456 | 0.0 |

The raw cooking-loss MAE is now `1.1078` across three papers. The diagnostic linear correction is effectively identity (`beta` near `1`), so raw model behavior is now more meaningful than post-hoc correction.

## Metric Summary

| Metric | MAE | RMSE | Bias | Interpretation |
|---|---:|---:|---:|---|
| `cooking_loss_pct` | 1.1078 | 1.3647 | 0.2267 | Good cross-source raw fit across three papers. |
| `water_absorption_pct` | 4.44 | 5.3165 | 0.1931 | Improved after stronger syneresis/water-release terms, still weakest metric. |
| `swelling_index` | 0.4973 | 0.6294 | 0.0041 | Directionally good for ratio-driven swelling. |

## Grouped Raw Error

By source:

| Source | Records | MAE | RMSE | Bias |
|---|---:|---:|---:|---:|
| `10.1002/fsn3.3301` | 30 | 1.0653 | 1.3146 | 0.3487 |
| `10.1016/j.fochx.2025.103403` | 5 | 1.158 | 1.2518 | -1.158 |
| `10.1007/s13197-016-2323-8` | 5 | 1.312 | 1.721 | 0.88 |

By process family:

| Process family | Records | MAE | RMSE | Bias |
|---|---:|---:|---:|---:|
| `fresh_calcium_gel` | 30 | 1.0653 | 1.3146 | 0.3487 |
| `dried_extruded` | 10 | 1.235 | 1.5048 | -0.139 |

By amaranth flour:water ratio:

| Ratio | MAE | RMSE | Bias |
|---|---:|---:|---:|
| `1:2` | 1.3817 | 1.7814 | 1.3383 |
| `1:4` | 1.105 | 1.4605 | 0.555 |
| `1:6` | 1.1033 | 1.2559 | 0.2833 |
| `1:8` | 0.995 | 1.0463 | -0.3517 |
| `1:10` | 0.7417 | 0.814 | -0.0817 |
| `unknown` | 0.582 | 0.741 | 0.566 |

By sodium alginate level:

| Alginate % | MAE | RMSE | Bias |
|---|---:|---:|---:|
| `0.0` | 0.582 | 0.741 | 0.566 |
| `1.0` | 1.3733 | 1.6612 | 1.276 |
| `1.5` | 0.7573 | 0.8347 | -0.5787 |

## Linear Correction

```text
corrected = -0.236598 + 1.001497 * simulated
```

This correction is diagnostic only. With three papers it is less obviously single-source-overfit, but the source count is still too small for production calibration.

## Rows

| ID | Time min | W:F | Measured | Simulated | Corrected | Residual Before | Gelation | Pregel | Syneresis |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| lux_2023_r1_2_alg1_5min | 5.0 | 2.0 | 1.79 | 2.91 | 1.7036 | 1.12 | 0.4717 | 0.8627 | 0.0 |
| lux_2023_r1_2_alg1_10min | 10.0 | 2.0 | 1.97 | 4.26 | 1.9213 | 2.29 | 0.4717 | 0.8627 | 0.0 |
| lux_2023_r1_2_alg1_15min | 15.0 | 2.0 | 2.27 | 5.68 | 2.1502 | 3.41 | 0.4717 | 0.8627 | 0.0 |
| lux_2023_r1_4_alg1_5min | 5.0 | 4.0 | 1.44 | 1.98 | 1.5536 | 0.54 | 0.5553 | 1.0 | 0.0067 |
| lux_2023_r1_4_alg1_10min | 10.0 | 4.0 | 1.77 | 3.2 | 1.7503 | 1.43 | 0.5553 | 1.0 | 0.0101 |
| lux_2023_r1_4_alg1_15min | 15.0 | 4.0 | 1.48 | 4.49 | 1.9584 | 3.01 | 0.5553 | 1.0 | 0.0117 |
| lux_2023_r1_6_alg1_5min | 5.0 | 6.0 | 0.98 | 1.55 | 1.4843 | 0.57 | 0.6389 | 1.0 | 0.0132 |
| lux_2023_r1_6_alg1_10min | 10.0 | 6.0 | 1.43 | 2.66 | 1.6633 | 1.23 | 0.6389 | 1.0 | 0.0197 |
| lux_2023_r1_6_alg1_15min | 15.0 | 6.0 | 1.46 | 3.82 | 1.8503 | 2.36 | 0.6389 | 1.0 | 0.0228 |
| lux_2023_r1_8_alg1_5min | 5.0 | 8.0 | 1.49 | 1.14 | 1.4182 | -0.35 | 0.7225 | 1.0 | 0.0149 |
| lux_2023_r1_8_alg1_10min | 10.0 | 8.0 | 1.26 | 2.12 | 1.5762 | 0.86 | 0.7225 | 1.0 | 0.0222 |
| lux_2023_r1_8_alg1_15min | 15.0 | 8.0 | 2.09 | 3.16 | 1.7439 | 1.07 | 0.7225 | 1.0 | 0.0258 |
| lux_2023_r1_10_alg1_5min | 5.0 | 10.0 | 1.34 | 0.96 | 1.3891 | -0.38 | 0.7464 | 0.9955 | 0.3937 |
| lux_2023_r1_10_alg1_10min | 10.0 | 10.0 | 1.3 | 1.87 | 1.5359 | 0.57 | 0.7464 | 0.9955 | 0.5864 |
| lux_2023_r1_10_alg1_15min | 15.0 | 10.0 | 1.44 | 2.85 | 1.6939 | 1.41 | 0.7464 | 0.9955 | 0.6808 |
| lux_2023_r1_2_alg1_5_5min | 5.0 | 2.0 | 1.52 | 1.39 | 1.4585 | -0.13 | 0.7076 | 0.8627 | 0.0 |
| lux_2023_r1_2_alg1_5_10min | 10.0 | 2.0 | 1.73 | 2.4 | 1.6213 | 0.67 | 0.7076 | 0.8627 | 0.0 |
| lux_2023_r1_2_alg1_5_15min | 15.0 | 2.0 | 2.79 | 3.46 | 1.7923 | 0.67 | 0.7076 | 0.8627 | 0.0 |
| lux_2023_r1_4_alg1_5_5min | 5.0 | 4.0 | 1.37 | 0.35 | 1.2908 | -1.02 | 0.8329 | 1.0 | 0.2126 |
| lux_2023_r1_4_alg1_5_10min | 10.0 | 4.0 | 1.59 | 0.99 | 1.394 | -0.6 | 0.8329 | 1.0 | 0.3167 |
| lux_2023_r1_4_alg1_5_15min | 15.0 | 4.0 | 1.88 | 1.85 | 1.5326 | -0.03 | 0.8329 | 1.0 | 0.3676 |
| lux_2023_r1_6_alg1_5_5min | 5.0 | 6.0 | 1.31 | 0.35 | 1.2908 | -0.96 | 0.9583 | 1.0 | 0.4158 |
| lux_2023_r1_6_alg1_5_10min | 10.0 | 6.0 | 1.03 | 0.35 | 1.2908 | -0.68 | 0.9583 | 1.0 | 0.6194 |
| lux_2023_r1_6_alg1_5_15min | 15.0 | 6.0 | 1.55 | 0.73 | 1.352 | -0.82 | 0.9583 | 1.0 | 0.719 |
| lux_2023_r1_8_alg1_5_5min | 5.0 | 8.0 | 1.5 | 0.35 | 1.2908 | -1.15 | 1.0837 | 1.0 | 0.4702 |
| lux_2023_r1_8_alg1_5_10min | 10.0 | 8.0 | 1.54 | 0.35 | 1.2908 | -1.19 | 1.0837 | 1.0 | 0.7004 |
| lux_2023_r1_8_alg1_5_15min | 15.0 | 8.0 | 1.7 | 0.35 | 1.2908 | -1.35 | 1.0837 | 1.0 | 0.8131 |
| lux_2023_r1_10_alg1_5_5min | 5.0 | 10.0 | 1.1 | 0.35 | 1.2908 | -0.75 | 1.1195 | 0.9955 | 0.6858 |
| lux_2023_r1_10_alg1_5_10min | 10.0 | 10.0 | 1.19 | 0.35 | 1.2908 | -0.84 | 1.1195 | 0.9955 | 1.0215 |
| lux_2023_r1_10_alg1_5_15min | 15.0 | 10.0 | 0.85 | 0.35 | 1.2908 | -0.5 | 1.1195 | 0.9955 | 1.1858 |
| liu_2026_rp_rf | 4.97 | None | 22.74 | 22.7 | 21.609 | -0.04 | 0.0 | 0.0 | 0.0 |
| liu_2026_rp_rk | 6.29 | None | 24.41 | 24.46 | 23.2995 | 0.05 | 0.0 | 0.0 | 0.0 |
| liu_2026_rp_rkc1 | 5.43 | None | 20.28 | 21.26 | 20.2259 | 0.98 | 0.0 | 0.0 | 0.0 |
| liu_2026_rp_rkc2 | 6.06 | None | 19.3 | 20.01 | 19.0252 | 0.71 | 0.0 | 0.0 | 0.0 |
| liu_2026_rp_rkc3 | 6.58 | None | 17.93 | 19.06 | 18.1127 | 1.13 | 0.0 | 0.0 | 0.0 |
| detchewa_2016_gfrs_spi0 | 17.6 | None | 25.4 | 24.95 | 24.7507 | -0.45 | 0.0 | 0.0 | 0.0 |
| detchewa_2016_gfrs_spi2_5 | 14.7 | None | 18.1 | 20.4 | 20.1939 | 2.3 | 0.0 | 0.0 | 0.0 |
| detchewa_2016_gfrs_spi5 | 13.7 | None | 17.0 | 17.2 | 16.9891 | 0.2 | 0.0 | 0.0 | 0.0 |
| detchewa_2016_gfrs_spi7_5 | 13.1 | None | 21.0 | 20.37 | 20.1639 | -0.63 | 0.0 | 0.0 | 0.0 |
| detchewa_2016_gfrs_spi10 | 13.1 | None | 21.8 | 24.78 | 24.5805 | 2.98 | 0.0 | 0.0 | 0.0 |

## Interpretation

The simulator now captures the main Lux 2023 mechanisms explicitly: calcium-mediated alginate gelation, flour:water ratio, pregelatinization, starch leaching, and syneresis/water release in high-water alginate gels. It also includes dried-extruded rice pasta branches for Liu 2026 and Detchewa 2016: KGM increases water uptake/cooking loss, curdlan reduces cooking loss through a heat-set gel network, and SPI has an optimum around 5% before high-protein disruption increases loss again.

Cooking-loss error improved substantially before any linear correction. The remaining pattern is useful: `1.0%` alginate is still overpredicted, while `1.5%` alginate is often underpredicted because the gelation term is probably too strong at high alginate.

The fitted correction is now essentially identity, which is a better diagnostic sign than the previous Lux-only correction. It still does not constitute production calibration because there are only three papers and two of them contribute just five records each.

## Model Implications

The current pasta model is more useful for screening both calcium-crosslinked alginate fresh pasta and dried-extruded rice pasta than the previous proxy. The strongest next improvement is broader cross-paper validation, not more coefficient tuning on these three sources.

## Next Calibration Steps

1. Extract more pasta papers with dried rice/corn systems and fresh pasta systems.
2. Add texture validation for Liu/Detchewa hardness, firmness, stickiness, and chewiness where table values are available.
3. Add digestibility/eGI as a separate functional objective for KGM/curdlan pasta.
4. Add uncertainty/confidence output to `/simulate/cooking` based on process family/source coverage.
5. Promote calibration confidence only after broader cross-paper validation.

## Limitations

- Dataset currently contains cooking-loss rows from three papers.
- Lux repeated rows share the same ingredient formulas, so the dataset is not independent in the statistical sense.
- Liu water absorption uses a different published equation and is converted to net uptake for simulator comparison.
- Detchewa water adsorption index is retained but excluded from current water-absorption metric summaries due to scale mismatch.
- Ingredient mapping is direct for current records, but ingredient composition values remain approximate.
- Linear correction is diagnostic only.
- A robust train/test split is still limited with only three papers.
