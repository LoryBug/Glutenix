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

`model_confidence` keeps the original scalar fields and adds structured confidence metadata:

- `score`: 0-1 diagnostic confidence score, independent from candidate ranking score.
- `level`: coarse legacy band, `low`, `medium`, or `high`.
- `confidence_summary`: one of `calibrated`, `literature_informed`, `heuristic`, or `ood_extrapolation`.
- `basis`: human-readable evidence notes.
- `risk_flags`: legacy human-readable warnings.
- `risk_warnings`: structured warnings with `tier`, `description`, `affected_variables`, and `severity`.

The confidence tier is not a quality score. A candidate can rank well while still being `heuristic` or `ood_extrapolation` if the formula/process is outside structured evidence coverage.

Current covered domains:

- `pasta_cooking` for `Pasta fresca`.
- `bread_baking` for `Pane`.

Unsupported applications such as pizza, sweet leavened doughs, and shortcrust are explicitly flagged as lacking structured literature coverage.

Important limitation: an in-range candidate is not automatically validated. It is only less extrapolative than a candidate outside the observed literature ranges.
