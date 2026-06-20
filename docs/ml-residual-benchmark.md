<!-- generated-start: ml-residual-benchmark -->
# ML Residual Model Benchmark Report

Date: 2026-06-20

## Summary

Classical ML models (ridge, RandomForest) trained on heuristic simulator residuals. All metrics use **leave-one-source-out cross-validation** to estimate generalization to unseen literature sources.

| Domain | Metric | Records | Sources | Heuristic MAE | Ridge MAE | Ridge Δ | RF MAE | RF Δ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| bread | `specific_volume_cm3_g` | 30 | 6 | 0.5054 | 3.3978 | -572.3% | 0.6752 | -33.6% |
| bread | `crumb_hardness_n` | 17 | 4 | 5.7347 | 28.9973 | -405.6% | 7.5429 | -31.5% |
| bread | `porosity_pct` | 11 | 3 | 7.5321 | 12.5985 | -67.3% | 11.3963 | -51.3% |
| pasta | `cooking_loss_pct` | 40 | 3 | 1.1077 | 6.4814 | -485.1% | 1.2143 | -9.6% |

## Bread: Specific Volume

**Records**: 30 &nbsp; **Sources**: 6

| Stage | MAE | RMSE | R² | Bias |
|---|---:|---:|---:|---:|
| Heuristic only | 0.5054 | 1.0795 | -0.0302 | -0.2885 |
| + Ridge residual | 3.3978 | 5.3757 | -24.5480 | -1.9173 |
| + RF residual | 0.6752 | 1.1117 | -0.0925 | +0.0263 |

**Leave-one-source-out folds**:

| Held-out source | Train | Test | Heuristic | +Ridge | +RF |
|---|---:|---:|:---|---:|:---:|
| `10.1038/s41598-021-93834-0` | 24 | 6 | MAE=0.3883 | MAE=11.4891 | MAE=0.6675 |
| `10.3390/foods11020199` | 27 | 3 | MAE=1.0526 | MAE=2.0676 | MAE=1.4152 |
| `10.3390/foods15020338` | 26 | 4 | MAE=0.2816 | MAE=1.0659 | MAE=0.1318 |
| `10.3390/foods15030412` | 28 | 2 | MAE=0.2820 | MAE=1.0791 | MAE=0.1920 |
| `10.3390/foods15101711` | 21 | 9 | MAE=0.1226 | MAE=1.1186 | MAE=0.3042 |
| `10.3390/foods9111548` | 24 | 6 | MAE=1.1466 | MAE=1.7178 | MAE=1.3928 |

## Bread: Crumb Hardness

**Records**: 17 &nbsp; **Sources**: 4

| Stage | MAE | RMSE | R² | Bias |
|---|---:|---:|---:|---:|
| Heuristic only | 5.7347 | 8.6809 | 0.1452 | +0.6221 |
| + Ridge residual | 28.9973 | 35.4863 | -13.2845 | -4.2579 |
| + RF residual | 7.5429 | 11.0781 | -0.3921 | -0.2993 |

**Leave-one-source-out folds**:

| Held-out source | Train | Test | Heuristic | +Ridge | +RF |
|---|---:|---:|:---|---:|:---:|
| `10.1038/s41598-021-93834-0` | 11 | 6 | MAE=3.1652 | MAE=21.8342 | MAE=2.7874 |
| `10.3390/foods11020199` | 14 | 3 | MAE=5.9852 | MAE=70.0949 | MAE=14.2003 |
| `10.3390/foods15030412` | 15 | 2 | MAE=2.0669 | MAE=25.4896 | MAE=3.2750 |
| `10.3390/foods9111548` | 11 | 6 | MAE=9.4016 | MAE=16.7808 | MAE=10.3924 |

## Bread: Porosity

**Records**: 11 &nbsp; **Sources**: 3

| Stage | MAE | RMSE | R² | Bias |
|---|---:|---:|---:|---:|
| Heuristic only | 7.5321 | 10.8127 | -0.4705 | +0.8222 |
| + Ridge residual | 12.5985 | 15.7926 | -2.1369 | +1.6126 |
| + RF residual | 11.3963 | 15.7214 | -2.1087 | -0.3786 |

**Leave-one-source-out folds**:

| Held-out source | Train | Test | Heuristic | +Ridge | +RF |
|---|---:|---:|:---|---:|:---:|
| `10.1002/fsn3.71107` | 5 | 6 | MAE=1.1929 | MAE=4.4145 | MAE=1.8314 |
| `10.3390/foods11020199` | 8 | 3 | MAE=12.3015 | MAE=20.1407 | MAE=21.5872 |
| `10.3390/foods15030412` | 9 | 2 | MAE=19.3955 | MAE=25.8371 | MAE=24.8047 |

## Pasta: Cooking Loss

**Records**: 40 &nbsp; **Sources**: 3

| Stage | MAE | RMSE | R² | Bias |
|---|---:|---:|---:|---:|
| Heuristic only | 1.1077 | 1.3647 | 0.9739 | +0.2267 |
| + Ridge residual | 6.4814 | 7.3204 | 0.2498 | -3.5206 |
| + RF residual | 1.2143 | 1.4427 | 0.9709 | -0.6576 |

**Leave-one-source-out folds**:

| Held-out source | Train | Test | Heuristic | +Ridge | +RF |
|---|---:|---:|:---|---:|:---:|
| `10.1002/fsn3.3301` | 10 | 30 | MAE=1.0653 | MAE=6.2817 | MAE=1.2162 |
| `10.1007/s13197-016-2323-8` | 35 | 5 | MAE=1.3120 | MAE=2.3768 | MAE=1.0646 |
| `10.1016/j.fochx.2025.103403` | 35 | 5 | MAE=1.1580 | MAE=11.7843 | MAE=1.3522 |

## Limitations

- Ridge and RandomForest residual correction is **diagnostic only**.
- Leave-one-source-out CV is a strong generalization test; small source counts limit model capacity.
- Feature vectors include blend composition + process parameters, not all possible confounders.
- No DL model is tested; scoped out until more records exist.
- These results inform the decision whether to integrate ML residual correction into production simulation.
- If integrated, correction must be gated by coverage/confidence to avoid extrapolation failure.

<!-- generated-end: ml-residual-benchmark -->