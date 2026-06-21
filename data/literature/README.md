# Literature Datasets

Datasets are newline-delimited JSON. Each line is one literature observation that can be traced back to a paper table, figure, or text excerpt.

Source metadata is centralized in `sources.json`. Each JSONL record must include a `source_id` that references an entry in that registry. The inline `source` object remains in records as convenience traceability metadata, but new public bibliography and source-count checks should use `sources.json` as the source of truth.

Current datasets:

- `sources.json`: source registry for all structured literature records.
- `pasta_cooking.jsonl`: gluten-free pasta cooking observations from 5 sources (42 records), including cooking loss and auxiliary water-uptake/swelling fields where available.
- `bread_baking.jsonl`: gluten-free bread baking observations from 10 sources (65 records), including Singh et al. 2026, Torres-Perez et al. 2026, Loncaric et al. 2026, Parsamajd et al. 2025, Belorio and Gomez 2020, Wojcik et al. 2021, Kahraman et al. 2022, Bianchi et al. 2026, Ghodosipoor et al. 2025, and Di Renzo et al. 2024, covering specific volume, crumb hardness, moisture, and auxiliary texture/structure fields where available.

Use `docs/literature-extraction-template.md` before adding a new paper. When adding a source, first add or update `sources.json`, then add JSONL records with the matching `source_id`, and finally regenerate the bibliography:

```bash
uv run python scripts/generate_bibliography.py
```

Dataset loading and validation live in `glutenix/calibration/literature.py`.
