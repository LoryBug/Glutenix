from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApplicationWorkflow:
    name: str
    status: str
    literature_domain: str | None
    target_profile: str
    flavor_target: str
    primary_metrics: tuple[str, ...]
    ranking_command: str | None
    dossier_command: str | None
    protocol_command: str | None
    feedback_command: str | None
    limitations: tuple[str, ...]
    next_requirements: tuple[str, ...]


WORKFLOWS = {
    "pane": ApplicationWorkflow(
        name="Pane",
        status="operational_v1",
        literature_domain="bread_baking",
        target_profile="Pane",
        flavor_target="Pane",
        primary_metrics=("specific_volume_cm3_g", "crumb_hardness_n", "porosity_pct", "protein_pct"),
        ranking_command="uv run glutenix rank-pane --preset bobs-inspired --save-run",
        dossier_command="uv run glutenix candidates report <candidate_id>",
        protocol_command="uv run glutenix candidates protocol <candidate_id> --batch-g 500",
        feedback_command="uv run glutenix feedback summary --application Pane",
        limitations=(
            "Bread predictions remain heuristic and require physical baking validation.",
            "Flavor explanation is not calibrated with sensory-panel data.",
            "Coverage is strongest for specific volume and weaker for full mechanism calibration.",
        ),
        next_requirements=(
            "Bake selected candidates and record matching numeric metrics.",
            "Use feedback summary to quantify model error before calibration decisions.",
        ),
    ),
    "pasta fresca": ApplicationWorkflow(
        name="Pasta fresca",
        status="experimental_v1",
        literature_domain="pasta_cooking",
        target_profile="Pasta fresca",
        flavor_target="Pasta fresca",
        primary_metrics=("cooking_loss_pct", "firmness_index", "water_uptake_pct", "protein_pct"),
        ranking_command="uv run glutenix rank-application --application 'Pasta fresca' --preset pasta-rice-structure-v1",
        dossier_command="uv run glutenix candidates report <candidate_id>",
        protocol_command="uv run glutenix candidates protocol <candidate_id> --batch-g 500",
        feedback_command="uv run glutenix feedback summary --application 'Pasta fresca'",
        limitations=(
            "Pasta v1 must not reuse bread quality metrics as pasta outcomes.",
            "Current pasta evidence is strongest for specific literature families and remains sparse for broad fresh pasta.",
            "Pasta v1 rankings remain heuristic and should be treated as formulation hypotheses until cooking tests exist.",
        ),
        next_requirements=(
            "Run saved Pasta fresca ranking campaigns with the pasta-rice-structure-v1 preset.",
            "Cook selected pasta candidates and record cooking loss, firmness, water uptake, protein, and sensory notes.",
        ),
    ),
}


def get_application_workflow(application: str) -> ApplicationWorkflow | None:
    return WORKFLOWS.get(application.strip().lower())


def list_application_workflows() -> list[ApplicationWorkflow]:
    return sorted(WORKFLOWS.values(), key=lambda workflow: workflow.name)


def expected_metrics_for_application(application: str) -> list[str]:
    workflow = get_application_workflow(application)
    return list(workflow.primary_metrics) if workflow else []
