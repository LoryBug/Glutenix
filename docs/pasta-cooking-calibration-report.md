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

- `amaranth_flour` -> `Quinoa flour` proxy.
- `sodium_alginate` -> `Xanthan gum` proxy.

These mappings are necessary because amaranth flour and sodium alginate are not currently present in the ingredient database.

## Error Summary

| Stage | MAE | RMSE | Bias |
|---|---:|---:|---:|
| Before correction | 7.0756 | 7.3370 | 7.0756 |
| After linear correction | 0.3727 | 0.4385 | -0.0000 |

## Linear Correction

```text
corrected = 0.999779 + 0.052685 * simulated
```

This correction is diagnostic only. It should not be treated as a production calibration because it is fitted on 9 records from one paper and uses ingredient proxies.

## Rows

| ID | Time min | Measured | Simulated | Corrected | Residual Before | Residual After |
|---|---:|---:|---:|---:|---:|---:|
| lux_2023_r1_2_alg1_5min | 5.0 | 1.79 | 6.10 | 1.3212 | 4.31 | -0.4688 |
| lux_2023_r1_2_alg1_10min | 10.0 | 1.97 | 8.61 | 1.4534 | 6.64 | -0.5166 |
| lux_2023_r1_2_alg1_15min | 15.0 | 2.27 | 10.98 | 1.5783 | 8.71 | -0.6917 |
| lux_2023_r1_6_alg1_5min | 5.0 | 0.98 | 6.10 | 1.3212 | 5.12 | 0.3412 |
| lux_2023_r1_6_alg1_10min | 10.0 | 1.43 | 8.61 | 1.4534 | 7.18 | 0.0234 |
| lux_2023_r1_6_alg1_15min | 15.0 | 1.46 | 10.98 | 1.5783 | 9.52 | 0.1183 |
| lux_2023_r1_10_alg1_5_5min | 5.0 | 1.10 | 5.97 | 1.3143 | 4.87 | 0.2143 |
| lux_2023_r1_10_alg1_5_10min | 10.0 | 1.19 | 8.50 | 1.4476 | 7.31 | 0.2576 |
| lux_2023_r1_10_alg1_5_15min | 15.0 | 0.85 | 10.87 | 1.5725 | 10.02 | 0.7225 |

## Interpretation

The current pasta simulator overpredicts cooking loss by approximately 7 percentage points for this literature dataset.

Likely reasons:

- Sodium alginate forms calcium-mediated gels in the Lux et al. process; xanthan is only a rough proxy.
- The study uses a gelation/extrusion process, not a conventional dough sheet.
- The simulator does not yet model calcium bath gel formation.
- Amaranth is approximated with quinoa flour, which changes protein/starch/fiber behavior.

## Model Implications

The cooking model is now directionally useful, but its absolute cooking-loss scale is too high for alginate-based fresh pasta. The strongest immediate improvement is adding sodium alginate as an ingredient with a specific cooking-loss retention factor.

## Next Calibration Steps

1. Add `Sodium alginate` to ingredient seed data.
2. Add an alginate-specific structure term in `PastaCookingSimulator`.
3. Add `Amaranth flour` to ingredient seed data or map it separately from quinoa.
4. Extract more pasta datasets with cooking loss, firmness, and water uptake.
5. Refit correction after at least 30 records from multiple papers.

## Limitations

- Dataset currently contains only cooking-loss examples from one paper.
- Ingredient mapping uses proxies.
- Linear correction is diagnostic only.
- No train/test split is meaningful at 9 records.
