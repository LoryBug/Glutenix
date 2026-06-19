# Literature Coverage and OOD Diagnostics

Date: 2026-06-19

Glutenix derives diagnostic coverage ranges from the structured JSONL literature datasets in `data/literature/`.

The coverage layer answers a different question from calibration error:

- Calibration error: how close are simulator outputs to measured metrics?
- Coverage/OOD: is this candidate formula and process inside the ingredient, blend-property, and process ranges already represented in structured literature records?

Current endpoint:

- `GET /calibration/coverage`

Current optimization integration:

- `POST /optimize/application-suggest` includes coverage/OOD basis and risk flags inside `model_confidence`.

Current covered domains:

- `pasta_cooking` for `Pasta fresca`.
- `bread_baking` for `Pane`.

Unsupported applications such as pizza, sweet leavened doughs, and shortcrust are explicitly flagged as lacking structured literature coverage.

Important limitation: an in-range candidate is not automatically validated. It is only less extrapolative than a candidate outside the observed literature ranges.
