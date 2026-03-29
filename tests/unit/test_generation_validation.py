from services.scenario_generator.defaults import get_default_environment_generation_service
from services.scenario_generator.models import EnvironmentKind, GenerationRequest, TaskKind
from services.scenario_generator.validation import merge_reports, validate_generation_request


def test_validate_generation_request_rejects_unsupported_combo():
    service = get_default_environment_generation_service()
    request = GenerationRequest(
        environment_kind=EnvironmentKind.CONTINUOUS_2D,
        task_kind=TaskKind.REFORESTATION,
        terrain_params={"grid_size": 10},
        forest_params={"obstacle_density": 0.2},
    )

    report = validate_generation_request(service.registry, request)

    assert report.passed is False
    assert any(issue.code == "unsupported_task_environment" for issue in report.issues)


def test_merge_reports_keeps_all_issues_and_pass_flag():
    service = get_default_environment_generation_service()
    request = GenerationRequest(
        environment_kind=EnvironmentKind.SIMULATOR_3D,
        task_kind=TaskKind.TRAIL,
        seed=7,
        terrain_params={"preview_size": 16},
        forest_params={"tree_density": 0.25},
        task_params={"max_steps": 20},
    )

    request_report = validate_generation_request(service.registry, request)
    scenario = service.generate(request)
    merged = merge_reports(request_report, scenario.validation_report)

    assert merged.passed is True
    assert merged.messages == scenario.validation_report.messages
