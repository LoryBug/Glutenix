# Literature Datasets

Datasets are newline-delimited JSON. Each line is one literature observation that can be traced back to a paper table, figure, or text excerpt.

Current datasets:

- `pasta_cooking.jsonl`: gluten-free pasta cooking observations from Lux et al. 2023, Liu et al. 2026, and Detchewa et al. 2016, including cooking loss and auxiliary water-uptake/swelling fields where available.

Use `docs/literature-extraction-template.md` before adding a new paper. Dataset loading and validation live in `glutenix/calibration/literature.py`.
