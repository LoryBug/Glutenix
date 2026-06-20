# Literature Datasets

Datasets are newline-delimited JSON. Each line is one literature observation that can be traced back to a paper table, figure, or text excerpt.

Current datasets:

- `pasta_cooking.jsonl`: gluten-free pasta cooking observations from Lux et al. 2023, Liu et al. 2026, and Detchewa et al. 2016, including cooking loss and auxiliary water-uptake/swelling fields where available.
- `bread_baking.jsonl`: gluten-free bread baking observations from 9 sources (60 records), including Singh et al. 2026, Torres-Perez et al. 2026, Loncaric et al. 2026, Parsamajd et al. 2025, Belorio and Gomez 2020, Wojcik et al. 2021, Kahraman et al. 2022, Bianchi et al. 2026, and Ghodosipoor et al. 2025, covering specific volume, crumb hardness, moisture, and auxiliary texture/structure fields where available.

Use `docs/literature-extraction-template.md` before adding a new paper. Dataset loading and validation live in `glutenix/calibration/literature.py`.
