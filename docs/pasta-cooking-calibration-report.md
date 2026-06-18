# Pasta Cooking Literature Calibration Report

Date: 2026-06-18

This report compares the current `PastaCookingSimulator` against literature cooking-loss examples extracted from Lux et al. 2023.

Source:

- Lux nee Bantleon T, Spillmann F, Reimold F, Erdos A, Lochny A, Floter E. `Physical quality of gluten-free doughs and fresh pasta made of amaranth`. Food Science & Nutrition, 2023, 11(6):3213-3223.
- DOI: `10.1002/fsn3.3301`
- PMCID: `PMC10261804`
- URL: `https://pmc.ncbi.nlm.nih.gov/articles/PMC10261804/`

## Dataset

Records: 9

Metric: `cooking_loss_pct`

Mapped ingredients:

- `amaranth_flour` -> `Amaranth flour`.
- `sodium_alginate` -> `Sodium alginate`.

These are now direct mappings after adding both ingredients to the database seed.

## Error Summary

| Stage | MAE | RMSE | Bias |
|---|---:|---:|---:|
| Before correction | 4.3789 | 4.8072 | 4.3789 |
| After linear correction | 0.3452 | 0.4108 | -0.0000 |

## Linear Correction

```text
corrected = 0.939584 + 0.087393 * simulated
```

This correction is diagnostic only. It should not be treated as a production calibration because it is fitted on 9 records from one paper and uses ingredient proxies.

## Rows

| ID | Time min | Measured | Simulated | Corrected | Residual Before | Residual After |
|---|---:|---:|---:|---:|---:|---:|
| lux_2023_r1_2_alg1_5min | 5.0 | 1.79 | 3.84 | 1.2752 | 2.05 | -0.5148 |
| lux_2023_r1_2_alg1_10min | 10.0 | 1.97 | 6.38 | 1.4971 | 4.41 | -0.4729 |
| lux_2023_r1_2_alg1_15min | 15.0 | 2.27 | 8.75 | 1.7043 | 6.48 | -0.5657 |
| lux_2023_r1_6_alg1_5min | 5.0 | 0.98 | 3.84 | 1.2752 | 2.86 | 0.2952 |
| lux_2023_r1_6_alg1_10min | 10.0 | 1.43 | 6.38 | 1.4971 | 4.95 | 0.0671 |
| lux_2023_r1_6_alg1_15min | 15.0 | 1.46 | 8.75 | 1.7043 | 7.29 | 0.2443 |
| lux_2023_r1_10_alg1_5_5min | 5.0 | 1.10 | 2.34 | 1.1441 | 1.24 | 0.0441 |
| lux_2023_r1_10_alg1_5_10min | 10.0 | 1.19 | 4.90 | 1.3678 | 3.71 | 0.1778 |
| lux_2023_r1_10_alg1_5_15min | 15.0 | 0.85 | 7.27 | 1.5749 | 6.42 | 0.7249 |

## Interpretation

The current pasta simulator still overpredicts cooking loss, but adding direct amaranth/alginate ingredients and an alginate retention term reduced the mean absolute error from 7.0756 to 4.3789 percentage points before correction.

Likely reasons:

- Sodium alginate forms calcium-mediated gels in the Lux et al. process; the simulator currently has only a simplified alginate retention term.
- The study uses a gelation/extrusion process, not a conventional dough sheet.
- The simulator does not yet model calcium bath gel formation.
- Amaranth flour parameters are approximate literature averages.

## Model Implications

The cooking model is now more directionally useful, but its absolute cooking-loss scale is still too high for alginate-based fresh pasta. The strongest next improvement is modeling calcium-mediated alginate gelation and flour:water ratio effects directly.

## Next Calibration Steps

1. Model calcium bath gel formation explicitly.
2. Add flour:water ratio as an input to `PastaCookingSimulator`.
3. Extract more pasta datasets with cooking loss, firmness, and water uptake.
4. Refit correction after at least 30 records from multiple papers.
5. Promote calibration confidence only after cross-paper validation.

## Limitations

- Dataset currently contains only cooking-loss examples from one paper.
- Ingredient mapping is now direct for amaranth and sodium alginate, but ingredient composition values remain approximate.
- Linear correction is diagnostic only.
- No train/test split is meaningful at 9 records.
