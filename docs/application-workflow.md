# Application Workflow Shape

Glutenix uses a small application workflow registry to keep product-specific assumptions explicit without building a heavy framework too early.

The registry lives in `glutenix/applications/workflow.py`.

## Workflow Fields

Each application workflow records:

- `name`: user-facing application name stored in runs, candidates, and reports.
- `status`: maturity label, for example `operational_v1` or `planned_v1`.
- `literature_domain`: structured coverage domain used by calibration and gap reports.
- `target_profile`: blend/process target profile name.
- `flavor_target`: flavor target name.
- `primary_metrics`: measurement names expected in protocols and feedback summaries.
- `ranking_command`: CLI path that can create ranked candidates, if implemented.
- `dossier_command`: CLI path for candidate decision reporting, if implemented.
- `protocol_command`: CLI path for physical-test planning, if implemented.
- `feedback_command`: CLI path for prediction-vs-measurement feedback.
- `limitations`: evidence, calibration, or mechanism boundaries.
- `next_requirements`: concrete requirements before the workflow matures.

## Current Workflows

### Pane

Status: `operational_v1`.

Pane supports the current full pre-lab loop:

- ranking and saved runs
- candidate decisions
- candidate dossier
- physical-test protocol
- coverage gaps
- sensitivity, cohort, and flavor diagnostics
- feedback summary after experiments are linked

Primary metrics:

- `specific_volume_cm3_g`
- `crumb_hardness_n`
- `porosity_pct`
- `protein_pct`

Limitations remain explicit: predictions are heuristic, flavor is not sensory-panel calibrated, and coverage is strongest for specific volume but weaker for full mechanism calibration.

### Pasta fresca

Status: `planned_v1`.

Pasta is the next intended vertical, but it must not reuse bread quality metrics as pasta outcomes.

Primary metrics planned for Pasta v1:

- `cooking_loss_pct`
- `firmness_index`
- `water_absorption_pct`
- `protein_pct`

Before Pasta ranking is implemented, the next task should document pasta targets, processing assumptions, and confidence limits from literature.

## Adding A New Application

1. Add or update an `ApplicationWorkflow` entry.
2. Define primary metrics before adding ranking logic.
3. Link the workflow to a literature coverage domain if structured coverage exists.
4. Document limitations before claiming operational status.
5. Add ranking/evaluation only after metric semantics and evidence boundaries are clear.
6. Preserve the diagnostic-only rule for sensitivity, flavor, coverage, and feedback summaries.
