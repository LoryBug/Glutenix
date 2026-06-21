from glutenix.applications.workflow import (
    expected_metrics_for_application,
    get_application_workflow,
    list_application_workflows,
)


def test_pane_workflow_is_operational():
    workflow = get_application_workflow("Pane")

    assert workflow is not None
    assert workflow.status == "operational_v1"
    assert workflow.literature_domain == "bread_baking"
    assert "specific_volume_cm3_g" in workflow.primary_metrics
    assert workflow.ranking_command is not None
    assert workflow.protocol_command is not None


def test_pasta_workflow_records_next_requirements():
    workflow = get_application_workflow("Pasta fresca")

    assert workflow is not None
    assert workflow.status == "planned_v1"
    assert workflow.literature_domain == "pasta_cooking"
    assert "cooking_loss_pct" in workflow.primary_metrics
    assert workflow.ranking_command is None
    assert workflow.next_requirements


def test_workflow_lookup_is_case_insensitive_and_metric_based():
    assert expected_metrics_for_application("pane") == [
        "specific_volume_cm3_g",
        "crumb_hardness_n",
        "porosity_pct",
        "protein_pct",
    ]
    assert expected_metrics_for_application("Unknown") == []


def test_list_application_workflows_is_sorted():
    names = [workflow.name for workflow in list_application_workflows()]

    assert names == sorted(names)
    assert {"Pane", "Pasta fresca"}.issubset(names)
